from __future__ import annotations

import argparse

from app.bootstrap.providers import (
    create_crawling_provider,
    create_email_verification_provider,
    create_gemini_provider,
    create_pagespeed_provider,
    create_wappalyzer_provider,
)
from app.core.database.session import SessionFactory
from app.core.logging import get_logger
from app.load.exports.webartsy import export_webartsy_leads
from app.models.schemas import DiscoveryQuery
from app.pipelines.webartsy.lead import run_webartsy_lead_pipeline
from app.providers.discovery.gosom import (
    GosomGoogleMapsDiscoveryProvider,
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def build_parser(
    parser: argparse.ArgumentParser | None = None,
) -> argparse.ArgumentParser:
    if parser is None:
        parser = argparse.ArgumentParser(
            description="Run the WebArtsy lead pipeline.",
        )

    parser.add_argument(
        "query",
        help="Business category or search query.",
    )

    parser.add_argument(
        "location",
        help="Geographic area.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Optional maximum number of deduplicated businesses "
            "to process. Omit to process all Gosom results."
        ),
    )

    # ------------------------------------------------------------------
    # Gosom discovery
    # ------------------------------------------------------------------

    parser.add_argument(
        "--proxy",
        default=None,
        help="Optional proxy URL for Google Maps extraction.",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of concurrent Gosom discovery jobs.",
    )

    parser.add_argument(
        "--depth",
        type=int,
        default=5,
        help="Maximum Google Maps result scroll depth.",
    )

    parser.add_argument(
        "--discovery-timeout",
        type=int,
        default=1800,
        help="Maximum Gosom discovery runtime in seconds.",
    )

    parser.add_argument(
        "--pages-per-browser",
        type=int,
        default=4,
        help="Maximum concurrent pages per Gosom browser process.",
    )

    parser.add_argument(
        "--browser-pool-size",
        type=int,
        default=1,
        help="Number of Gosom browser processes.",
    )

    # ------------------------------------------------------------------
    # Grid search
    # ------------------------------------------------------------------

    parser.add_argument(
        "--grid-bbox",
        default=None,
        help=(
            "Geographic grid bounding box in the format "
            "minLat,minLon,maxLat,maxLon."
        ),
    )

    parser.add_argument(
        "--grid-cell-km",
        type=float,
        default=1.0,
        help="Grid cell size in kilometers.",
    )

    parser.add_argument(
        "--zoom",
        type=int,
        default=16,
        help="Google Maps zoom level used for grid searches.",
    )

    # ------------------------------------------------------------------
    # WebArtsy company workers
    # ------------------------------------------------------------------

    parser.add_argument(
        "--company-workers",
        type=int,
        default=2,
        help=(
            "Number of companies processed concurrently "
            "during WebArtsy enrichment."
        ),
    )

    parser.add_argument(
        "--company-retries",
        type=int,
        default=1,
        help=(
            "Number of retries for transient company "
            "enrichment failures."
        ),
    )

    parser.add_argument(
        "--company-queue-size",
        type=int,
        default=None,
        help=(
            "Maximum number of companies buffered in the "
            "worker queue. Defaults to 2x company workers."
        ),
    )

    # ------------------------------------------------------------------
    # Website analysis
    # ------------------------------------------------------------------

    parser.add_argument(
        "--phone-region",
        default=None,
        help="Phone normalization region, e.g. NL, GB, PK.",
    )

    parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
        help="Website crawl retention period.",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Per-website network/crawl timeout in seconds.",
    )

    parser.add_argument(
        "--business-page-limit",
        type=int,
        default=5,
        help=(
            "Maximum number of relevant business pages "
            "to crawl per company."
        ),
    )

    parser.add_argument(
        "--decision-maker-limit",
        type=int,
        default=5,
        help="Maximum classified decision makers per company.",
    )

    parser.add_argument(
        "--person-email-limit",
        type=int,
        default=None,
        help=(
            "Maximum number of persisted people with known emails "
            "to verify per company. Defaults to all."
        ),
    )

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    parser.add_argument(
        "--export-dir",
        default="exports",
        help="Directory for CSV exports.",
    )

    return parser


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


async def run(
    args: argparse.Namespace,
) -> None:
    query = DiscoveryQuery(
        query=args.query,
        location=args.location,
        limit=args.limit,
    )

    # =========================================================
    # Providers
    # =========================================================

    discovery_provider = GosomGoogleMapsDiscoveryProvider(
        proxy=args.proxy,
        concurrency=args.workers,
        depth=args.depth,
        zoom=args.zoom,
        grid_bbox=args.grid_bbox,
        grid_cell_km=args.grid_cell_km,
        timeout_seconds=args.discovery_timeout,
        pages_per_browser=args.pages_per_browser,
        browser_pool_size=args.browser_pool_size,
    )

    crawler_provider = (
        create_crawling_provider()
    )

    technology_provider = (
        create_wappalyzer_provider()
    )

    performance_provider = (
        create_pagespeed_provider()
    )

    gemini_provider = (
        create_gemini_provider()
    )

    email_provider = (
        create_email_verification_provider()
    )

    # PageSpeed currently also provides SEO analysis.
    seo_provider = performance_provider

    # =========================================================
    # Start
    # =========================================================

    logger.info(
        "webartsy_cli_started",

        # Discovery
        query=args.query,
        location=args.location,
        limit=args.limit,
        discovery_workers=args.workers,
        depth=args.depth,
        discovery_timeout=args.discovery_timeout,
        grid_bbox=args.grid_bbox,
        grid_cell_km=args.grid_cell_km,
        zoom=args.zoom,
        pages_per_browser=args.pages_per_browser,
        browser_pool_size=args.browser_pool_size,

        # Company processing
        company_workers=args.company_workers,
        company_retries=args.company_retries,
        company_queue_size=args.company_queue_size,



        # Analysis
        website_timeout=args.timeout,
        retention_days=args.retention_days,
        business_page_limit=args.business_page_limit,
        decision_maker_limit=args.decision_maker_limit,
        person_email_limit=args.person_email_limit,
        phone_region=args.phone_region,
    )

    # =========================================================
    # Pipeline
    # =========================================================

    async with SessionFactory() as session:
        result = await run_webartsy_lead_pipeline(
            session=session,
            discovery_provider=discovery_provider,
            query=query,
            crawler_provider=crawler_provider,
            technology_provider=technology_provider,
            performance_provider=performance_provider,
            seo_provider=seo_provider,
            email_provider=email_provider,
            gemini_provider=gemini_provider,
            phone_region=args.phone_region,
            source_id=None,
            retention_days=args.retention_days,
            timeout=args.timeout,
            decision_maker_limit=args.decision_maker_limit,
            person_email_limit=args.person_email_limit,
            business_page_limit=args.business_page_limit,

            company_workers=args.company_workers,
            company_queue_size=args.company_queue_size,
            company_retries=args.company_retries,
        )

        # -----------------------------------------------------
        # Export only after the full pipeline completes.
        # PostgreSQL remains the source of truth.
        # -----------------------------------------------------

        export_path = await export_webartsy_leads(
            session=session,
            output_dir=args.export_dir,
        )

    # =========================================================
    # Completed
    # =========================================================

    logger.info(
        "webartsy_lead_pipeline_completed",
        found=result.discovery.found,
        new=result.discovery.new,
        duplicates=result.discovery.duplicates,
        stored=result.discovery.stored,
        companies_analyzed=result.companies_analyzed,
        companies_failed=result.companies_failed,
        people_found=result.people_found,
        decision_makers_found=result.decision_makers_found,
        technologies_detected=result.technology.detected,
        technology_failed=result.technology.failed,
        technology_stored=result.technology.stored,
        performance_analyzed=result.performance.analyzed,
        performance_failed=result.performance.failed,
        performance_stored=result.performance.stored,
        company_workers=args.company_workers,
        export_path=str(export_path),
    )

    print_webartsy_result(
        result,
        export_path=export_path,
        args=args,
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def print_webartsy_result(
    result,
    *,
    export_path,
    args: argparse.Namespace | None = None,
) -> None:
    print()
    print("=" * 80)
    print("WebArtsy Lead Pipeline")
    print("=" * 80)

    # =========================================================
    # Configuration
    # =========================================================

    if args is not None:
        print()
        print("Configuration")

        print(
            f"  Query:              "
            f"{args.query}"
        )

        print(
            f"  Location:           "
            f"{args.location}"
        )

        print(
            f"  Limit:              "
            f"{args.limit if args.limit is not None else 'unlimited'}"
        )

        print(
            f"  Gosom workers:      "
            f"{args.workers}"
        )

        print(
            f"  Company workers:    "
            f"{args.company_workers}"
        )

        print(
            f"  Company retries:    "
            f"{args.company_retries}"
        )

        print(
            f"  Company queue:      "
            f"{args.company_queue_size or 'auto'}"
        )

        print(
            f"  Depth:              "
            f"{args.depth}"
        )

        print(
            f"  Discovery timeout:  "
            f"{args.discovery_timeout}s"
        )

        if args.grid_bbox:
            print(
                f"  Grid bbox:          "
                f"{args.grid_bbox}"
            )

            print(
                f"  Grid cell:          "
                f"{args.grid_cell_km} km"
            )

            print(
                f"  Grid zoom:          "
                f"{args.zoom}"
            )

        print(
            f"  Browser pool:       "
            f"{args.browser_pool_size}"
        )

        print(
            f"  Pages/browser:      "
            f"{args.pages_per_browser}"
        )

        print(
            f"  Crawl timeout:      "
            f"{args.timeout}s"
        )

        print(
            f"  Business pages:     "
            f"{args.business_page_limit}"
        )

    # =========================================================
    # Discovery
    # =========================================================

    print()
    print("Discovery")

    print(
        f"  Found:             "
        f"{result.discovery.found}"
    )

    print(
        f"  New:               "
        f"{result.discovery.new}"
    )

    print(
        f"  Duplicates:        "
        f"{result.discovery.duplicates}"
    )

    print(
        f"  Stored:            "
        f"{result.discovery.stored}"
    )

    # =========================================================
    # Pipeline
    # =========================================================

    print()
    print("Pipeline")

    print(
        f"  Companies:         "
        f"{result.companies_analyzed}"
    )

    print(
        f"  Failed companies:  "
        f"{result.companies_failed}"
    )

    print(
        f"  People:            "
        f"{result.people_found}"
    )

    print(
        f"  Decision makers:   "
        f"{result.decision_makers_found}"
    )

    print(
        f"  Person email limit: "
        f"{args.person_email_limit if args.person_email_limit is not None else 'all'}"
    )

    # =========================================================
    # Technology
    # =========================================================

    print()
    print("Technology")

    print(
        f"  Detected:          "
        f"{result.technology.detected}"
    )

    print(
        f"  Failed:            "
        f"{result.technology.failed}"
    )

    print(
        f"  Stored:            "
        f"{result.technology.stored}"
    )

    # =========================================================
    # Performance
    # =========================================================

    print()
    print("Performance / SEO")

    print(
        f"  Analyzed:          "
        f"{result.performance.analyzed}"
    )

    print(
        f"  Failed:            "
        f"{result.performance.failed}"
    )

    print(
        f"  Stored:            "
        f"{result.performance.stored}"
    )

    print()
    print(
        f"CSV export: {export_path}"
    )

    print()
    print("-" * 80)

    # =========================================================
    # Per-company output
    # =========================================================

    for company in result.companies:
        print()
        print("  Website")

        if company.website_analysis is None:
            print("    Missing")

        else:
            website = company.website_analysis.content

            print(
                f"    Status: "
                f"{website.status_code}"
            )

            print(
                f"    Title: "
                f"{website.title}"
            )

            print(
                f"    HTML: "
                f"{len(website.html or '')} chars"
            )

            print(
                f"    Text: "
                f"{len(website.text or '')} chars"
            )

            print(
                f"    Links: "
                f"{len(website.links)}"
            )

            print(
                f"    Pages processed: "
                f"{company.pages_processed}"
            )

        # -----------------------------------------------------
        # Contacts
        # -----------------------------------------------------

        contacts = (
            company.contacts.contacts
        )

        print()
        print("  Contacts")

        print(
            f"    Emails: "
            f"{len(contacts.emails)}"
        )

        print(
            f"    Phones: "
            f"{len(contacts.phones)}"
        )

        print(
            "    LinkedIn companies: "
            f"{len(contacts.linkedin_company_urls)}"
        )

        print(
            "    LinkedIn profiles: "
            f"{len(contacts.linkedin_profile_urls)}"
        )

        print(
            f"    Facebook: "
            f"{len(contacts.facebook_urls)}"
        )

        print(
            f"    Instagram: "
            f"{len(contacts.instagram_urls)}"
        )

        print(
            f"    X: "
            f"{len(contacts.x_urls)}"
        )

        print(
            f"    YouTube: "
            f"{len(contacts.youtube_urls)}"
        )

        print(
            f"    GitHub: "
            f"{len(contacts.github_urls)}"
        )

        print(
            f"    TikTok: "
            f"{len(contacts.tiktok_urls)}"
        )

        # -----------------------------------------------------
        # People
        # -----------------------------------------------------

        print()
        print("  People")

        if not company.people:
            print(
                "    None found"
            )

        else:
            for analyzed_person in company.people:
                person = (
                    analyzed_person.person
                )

                linkedin = (
                    str(
                        person.linkedin_url
                    )
                    if person.linkedin_url
                    else "-"
                )

                print(
                    f"    - {person.name} | "
                    f"{person.title or '-'} | "
                    f"{linkedin} | "
                    f"score={analyzed_person.score} | "
                    f"role={analyzed_person.role_group} | "
                    f"decision_maker="
                    f"{analyzed_person.is_decision_maker}"
                )

        # -----------------------------------------------------
        # Decision makers
        # -----------------------------------------------------

        print()
        print("  Decision Makers")

        if not company.decision_makers:
            print(
                "    None found"
            )

        else:
            for analyzed_person in company.decision_makers:
                person = (
                    analyzed_person.person
                )

                category = getattr(
                    analyzed_person,
                    "decision_maker_category",
                    None,
                )

                print(
                    f"    - {person.name} | "
                    f"{person.title or '-'} | "
                    f"score={analyzed_person.score} | "
                    f"role={analyzed_person.role_group} | "
                    f"category={category or '-'} | "
                    f"confidence={analyzed_person.confidence}"
                )

                print(
                    f"      reasons="
                    f"{analyzed_person.reasons}"
                )

        print()
        print("  Person Email Verification")

        email_analysis = company.person_email_analysis

        if email_analysis is None:
            print("    Not run")

        else:
            print(
                f"    Attempted: "
                f"{email_analysis.attempted_count}"
            )

            print(
                f"    Verified: "
                f"{email_analysis.verified_count}"
            )

            print(
                f"    Qualified: "
                f"{email_analysis.qualified_count}"
            )

            print(
                f"    Failed: "
                f"{email_analysis.failed_count}"
            )

            print(
                f"    Persisted: "
                f"{email_analysis.persisted_count}"
            )

            for person_result in email_analysis.people:
                print(
                    f"    - {person_result.person_name} | "
                    f"{person_result.email} | "
                    f"status={person_result.status} | "
                    f"confidence={person_result.confidence:.2f} | "
                    f"qualified={person_result.is_qualified}"
                )

                print(
                    f"      reason="
                    f"{person_result.qualification_reason}"
                )

    # =========================================================
    # Failures
    # =========================================================

    if result.failures:
        print()
        print("-" * 80)

        print()
        print("Failures")

        for failure in result.failures:
            print(
                f"  - {failure.company_name} | "
                f"stage={failure.stage} | "
                f"{failure.error_type}: "
                f"{failure.error_message}"
            )

    print()
    print("=" * 80)
    print("WebArtsy pipeline completed.")
    print("=" * 80)