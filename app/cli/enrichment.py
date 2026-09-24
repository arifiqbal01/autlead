from __future__ import annotations

import argparse
from datetime import datetime

from app.bootstrap.providers import (
    create_crawling_provider,
    create_email_verification_provider,
    create_groq_provider,
    create_pagespeed_provider,
    create_wappalyzer_provider,
)
from app.core.logging import get_logger
from app.pipelines.enrichment.core import (
    EnrichmentPipelineResult,
    run_enrichment_pipeline,
)


logger = get_logger(__name__)


def build_parser(
    parser: argparse.ArgumentParser | None = None,
) -> argparse.ArgumentParser:
    if parser is None:
        parser = argparse.ArgumentParser(
            description=(
                "Run enrichment against companies "
                "already stored in PostgreSQL."
            ),
        )

    parser.add_argument(
        "--start-from",
        type=datetime.fromisoformat,
        default=None,
        help=(
            "Optional company created_at lower bound. "
            "Example: 2026-08-20T00:00:00+00:00"
        ),
    )

    parser.add_argument(
        "--after-company-id",
        type=int,
        default=None,
        help=(
            "Only process companies whose ID is greater "
            "than this value."
        ),
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help=(
            "Number of companies loaded from PostgreSQL "
            "per batch."
        ),
    )

    parser.add_argument(
        "--max-companies",
        type=int,
        default=None,
        help=(
            "Optional maximum number of companies to process "
            "during this run."
        ),
    )

    parser.add_argument(
        "--company-workers",
        type=int,
        default=2,
        help=(
            "Number of companies enriched concurrently."
        ),
    )

    parser.add_argument(
        "--company-retries",
        type=int,
        default=1,
        help=(
            "Number of retries for transient company failures."
        ),
    )

    parser.add_argument(
        "--company-queue-size",
        type=int,
        default=None,
        help=(
            "Maximum worker queue size. "
            "Defaults to the worker-pool implementation default."
        ),
    )

    parser.add_argument(
        "--phone-region",
        default=None,
        help=(
            "Phone normalization region, e.g. NL, GB, PK."
        ),
    )

    parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
        help=(
            "Website crawl retention period."
        ),
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help=(
            "Per-company website/network timeout."
        ),
    )

    parser.add_argument(
        "--business-page-limit",
        type=int,
        default=5,
        help=(
            "Maximum number of relevant business pages "
            "processed per company."
        ),
    )

    parser.add_argument(
        "--decision-maker-limit",
        type=int,
        default=5,
        help=(
            "Maximum number of classified decision makers "
            "per company."
        ),
    )

    parser.add_argument(
        "--person-email-limit",
        type=int,
        default=None,
        help=(
            "Maximum number of persisted people to process "
            "for email enrichment per company. "
            "Defaults to all."
        ),
    )

    parser.add_argument(
        "--language",
        default="nl",
        help=(
            "Language used for people analysis."
        ),
    )

    return parser


async def run(
    args: argparse.Namespace,
) -> None:
    crawler_provider = (
        create_crawling_provider()
    )

    groq_provider = (
        create_groq_provider()
    )

    technology_provider = (
        create_wappalyzer_provider()
    )

    performance_provider = (
        create_pagespeed_provider()
    )

    email_provider = (
        create_email_verification_provider()
    )

    # PageSpeed currently provides both performance
    # and SEO analysis.
    seo_provider = performance_provider

    logger.info(
        "enrichment_cli_started",
        start_from=(
            args.start_from.isoformat()
            if args.start_from is not None
            else None
        ),
        after_company_id=(
            args.after_company_id
        ),
        batch_size=(
            args.batch_size
        ),
        max_companies=(
            args.max_companies
        ),
        company_workers=(
            args.company_workers
        ),
        company_retries=(
            args.company_retries
        ),
        company_queue_size=(
            args.company_queue_size
        ),
        phone_region=(
            args.phone_region
        ),
        retention_days=(
            args.retention_days
        ),
        timeout=(
            args.timeout
        ),
        business_page_limit=(
            args.business_page_limit
        ),
        decision_maker_limit=(
            args.decision_maker_limit
        ),
        person_email_limit=(
            args.person_email_limit
        ),
        language=(
            args.language
        ),
        llm_provider="groq",
    )

    result = await run_enrichment_pipeline(
        crawler_provider=crawler_provider,
        technology_provider=technology_provider,
        performance_provider=performance_provider,
        seo_provider=seo_provider,
        email_provider=email_provider,
        groq_provider=groq_provider,
        start_from=args.start_from,
        after_company_id=args.after_company_id,
        batch_size=args.batch_size,
        max_companies=args.max_companies,
        company_workers=args.company_workers,
        company_queue_size=(
            args.company_queue_size
        ),
        company_retries=(
            args.company_retries
        ),
        phone_region=args.phone_region,
        source_id=None,
        retention_days=(
            args.retention_days
        ),
        timeout=args.timeout,
        decision_maker_limit=(
            args.decision_maker_limit
        ),
        person_email_limit=(
            args.person_email_limit
        ),
        business_page_limit=(
            args.business_page_limit
        ),
        language=args.language,
    )

    logger.info(
        "enrichment_cli_completed",
        selected=result.selected,
        succeeded=result.succeeded,
        failed=result.failed,
        companies_with_website=(
            result.companies_with_website
        ),
        companies_without_website=(
            result.companies_without_website
        ),
        people_found=(
            result.people_found
        ),
        decision_makers_found=(
            result.decision_makers_found
        ),
        last_company_id=(
            result.last_company_id
        ),
        llm_provider="groq",
    )

    print_result(
        result,
        args=args,
    )


def print_result(
    result: EnrichmentPipelineResult,
    *,
    args: argparse.Namespace,
) -> None:
    print()
    print("=" * 80)
    print("Enrichment Pipeline")
    print("=" * 80)

    print()
    print("Configuration")

    print(
        f"  Start from:        "
        f"{args.start_from or '-'}"
    )

    print(
        f"  After company ID:  "
        f"{args.after_company_id or '-'}"
    )

    print(
        f"  Batch size:        "
        f"{args.batch_size}"
    )

    print(
        f"  Max companies:     "
        f"{args.max_companies or 'unlimited'}"
    )

    print(
        f"  Company workers:   "
        f"{args.company_workers}"
    )

    print(
        f"  Company retries:   "
        f"{args.company_retries}"
    )

    print(
        f"  Company queue:     "
        f"{args.company_queue_size or 'auto'}"
    )

    print(
        f"  Phone region:      "
        f"{args.phone_region or '-'}"
    )

    print(
        f"  Retention days:    "
        f"{args.retention_days}"
    )

    print(
        f"  Timeout:           "
        f"{args.timeout}"
    )

    print(
        f"  Business pages:    "
        f"{args.business_page_limit}"
    )

    print(
        f"  Decision makers:   "
        f"{args.decision_maker_limit}"
    )

    print(
        f"  Person emails:     "
        f"{(
            args.person_email_limit
            if args.person_email_limit is not None
            else 'all'
        )}"
    )

    print(
        f"  Language:          "
        f"{args.language}"
    )

    print(
        "  LLM provider:      "
        "Groq"
    )

    print()
    print("Result")

    print(
        f"  Selected:          "
        f"{result.selected}"
    )

    print(
        f"  Succeeded:         "
        f"{result.succeeded}"
    )

    print(
        f"  Failed:            "
        f"{result.failed}"
    )

    print(
        f"  With website:      "
        f"{result.companies_with_website}"
    )

    print(
        f"  Without website:   "
        f"{result.companies_without_website}"
    )

    print(
        f"  People found:      "
        f"{result.people_found}"
    )

    print(
        f"  Decision makers:   "
        f"{result.decision_makers_found}"
    )

    print(
        f"  Last company ID:   "
        f"{result.last_company_id or '-'}"
    )

    if result.failures:
        print()
        print("Failures")

        for failure in result.failures:
            print(
                f"  - {failure.company_name} "
                f"(ID={failure.company_id}) | "
                f"stage={failure.stage} | "
                f"{failure.error_type}: "
                f"{failure.error_message}"
            )

    print()
    print("=" * 80)