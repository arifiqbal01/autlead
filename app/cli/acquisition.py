from __future__ import annotations

import argparse

from app.bootstrap.providers import (
    create_gosom_discovery_provider,
)
from app.core.config.acquisition_plan import (
    load_acquisition_plan,
)
from app.core.logging import get_logger
from app.models.schemas.acquisition_plan import (
    AcquisitionCity,
)
from app.models.schemas import (
    DiscoveryQuery,
)
from app.pipelines.acquisition.pipeline import (
    run_acquisition_pipeline,
)
from app.pipelines.acquisition.plan import (
    run_acquisition_plan,
)
from app.providers.discovery.protocol import (
    BusinessDiscoveryProvider,
)
from app.providers.discovery.gosom_import import (
    GosomResultsFileDiscoveryProvider,
)


logger = get_logger(__name__)


def build_parser(
    parser: argparse.ArgumentParser | None = None,
) -> argparse.ArgumentParser:
    if parser is None:
        parser = argparse.ArgumentParser(
            description="Run the Autlead acquisition pipeline.",
        )

    subparsers = parser.add_subparsers(
        dest="acquisition_command",
        required=True,
    )

    search_parser = subparsers.add_parser(
        "search",
        help="Run a single business discovery search.",
    )

    search_parser.add_argument(
        "query",
        help="Business category or search query, e.g. tandarts.",
    )

    search_parser.add_argument(
        "location",
        help="Geographic area, e.g. Amsterdam, Nederland.",
    )

    _add_runtime_arguments(search_parser)
    _add_search_grid_arguments(search_parser)

    plan_parser = subparsers.add_parser(
        "plan",
        help="Run an acquisition plan from YAML configuration.",
    )

    plan_parser.add_argument(
        "plan_name",
        help="Acquisition plan name, e.g. nl_healthcare.",
    )

    _add_runtime_arguments(plan_parser)


    import_parser = subparsers.add_parser(
        "import-results",
        help="Import an existing Gosom results.csv without scraping.",
    )

    import_parser.add_argument(
        "results_file",
        help="Path to an existing Gosom results.csv.",
    )

    import_parser.add_argument(
        "query",
        help="Original discovery query, e.g. tandarts.",
    )

    import_parser.add_argument(
        "location",
        help="Original discovery location, e.g. Amsterdam, Netherlands.",
    )

    import_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of businesses to import after deduplication.",
    )

    return parser


def _add_runtime_arguments(
    parser: argparse.ArgumentParser,
) -> None:
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Maximum number of businesses to return "
            "per discovery query after deduplication."
        ),
    )

    parser.add_argument(
        "--proxy",
        default=None,
        help="Optional proxy URL for Google Maps extraction.",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of concurrent Gosom scrape jobs.",
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
        help="Concurrent pages per browser process.",
    )

    parser.add_argument(
        "--browser-pool-size",
        type=int,
        default=1,
        help="Maximum number of Gosom browser processes.",
    )


def _add_search_grid_arguments(
    parser: argparse.ArgumentParser,
) -> None:
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


async def run(args: argparse.Namespace) -> None:
    if args.acquisition_command == "search":
        await _run_search(args=args)
        return

    if args.acquisition_command == "plan":
        await _run_plan(args=args)
        return

    if args.acquisition_command == "import-results":
        await _run_import_results(args=args)
        return

    raise ValueError(
        f"Unknown acquisition command: "
        f"{args.acquisition_command}"
    )


async def _run_search(
    *,
    args: argparse.Namespace,
) -> None:
    query = DiscoveryQuery(
        query=args.query,
        location=args.location,
        limit=args.limit,
    )

    provider = create_gosom_discovery_provider(
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

    logger.info(
        "acquisition_cli_started",
        mode="search",
        query=query.query,
        location=query.location,
        limit=query.limit,
        workers=args.workers,
        depth=args.depth,
        grid_bbox=args.grid_bbox,
        grid_cell_km=args.grid_cell_km,
        zoom=args.zoom,
        discovery_timeout=args.discovery_timeout,
        pages_per_browser=args.pages_per_browser,
        browser_pool_size=args.browser_pool_size,
    )

    result = await run_acquisition_pipeline(
        provider=provider,
        query=query,
    )

    logger.info(
        "acquisition_cli_completed",
        mode="search",
        found=result.found,
        new=result.new,
        duplicates=result.duplicates,
        stored=result.stored,
    )

    print()
    print("=" * 80)
    print("Autlead Acquisition")
    print("=" * 80)

    print()
    print(f"Query:              {query.query}")
    print(f"Location:           {query.location}")
    print(f"Limit:              {query.limit}")
    print(f"Workers:            {args.workers}")
    print(f"Depth:              {args.depth}")
    print(
        f"Discovery timeout:  "
        f"{args.discovery_timeout}s"
    )

    if args.grid_bbox:
        print(f"Grid bbox:          {args.grid_bbox}")
        print(
            f"Grid cell:          "
            f"{args.grid_cell_km} km"
        )
        print(f"Zoom:               {args.zoom}")

    print()
    print("Results")
    print(f"  Found:            {result.found}")
    print(f"  New:              {result.new}")
    print(f"  Duplicates:       {result.duplicates}")
    print(f"  Stored:           {result.stored}")
    print()


async def _run_plan(
    *,
    args: argparse.Namespace,
) -> None:
    plan = load_acquisition_plan(
        args.plan_name,
    )

    def provider_factory(
        city: AcquisitionCity,
    ) -> BusinessDiscoveryProvider:
        return create_gosom_discovery_provider(
            proxy=args.proxy,
            concurrency=args.workers,
            depth=args.depth,
            zoom=city.zoom,
            grid_bbox=city.grid_bbox,
            grid_cell_km=city.grid_cell_km,
            timeout_seconds=args.discovery_timeout,
            pages_per_browser=args.pages_per_browser,
            browser_pool_size=args.browser_pool_size,
        )

    logger.info(
        "acquisition_cli_started",
        mode="plan",
        plan=plan.name,
        country=plan.country.code,
        industry=plan.industry,
        cities=len(plan.cities),
        limit=args.limit,
        workers=args.workers,
        depth=args.depth,
        discovery_timeout=args.discovery_timeout,
        pages_per_browser=args.pages_per_browser,
        browser_pool_size=args.browser_pool_size,
    )

    result = await run_acquisition_plan(
        plan=plan,
        provider_factory=provider_factory,
        limit=args.limit,
    )

    logger.info(
        "acquisition_cli_completed",
        mode="plan",
        plan=plan.name,
        queries=result.queries,
        found=result.found,
        new=result.new,
        duplicates=result.duplicates,
        stored=result.stored,
    )

    print()
    print("=" * 80)
    print("Autlead Acquisition Plan")
    print("=" * 80)

    print()
    print(f"Plan:               {plan.name}")
    print(f"Country:            {plan.country.name}")
    print(f"Industry:           {plan.industry}")
    print(f"Cities:             {len(plan.cities)}")
    print(f"Limit/query:        {args.limit}")
    print(f"Workers:            {args.workers}")
    print(f"Depth:              {args.depth}")
    print(
        f"Discovery timeout:  "
        f"{args.discovery_timeout}s"
    )

    print()
    print("Results")
    print(f"  Queries:          {result.queries}")
    print(f"  Found:            {result.found}")
    print(f"  New:              {result.new}")
    print(f"  Duplicates:       {result.duplicates}")
    print(f"  Stored:           {result.stored}")
    print()


async def _run_import_results(
    *,
    args: argparse.Namespace,
) -> None:
    query = DiscoveryQuery(
        query=args.query,
        location=args.location,
        limit=args.limit,
    )

    provider = GosomResultsFileDiscoveryProvider(
        results_file=args.results_file,
    )

    logger.info(
        "acquisition_cli_started",
        mode="import_results",
        results_file=args.results_file,
        query=query.query,
        location=query.location,
        limit=query.limit,
    )

    result = await run_acquisition_pipeline(
        provider=provider,
        query=query,
    )

    logger.info(
        "acquisition_cli_completed",
        mode="import_results",
        results_file=args.results_file,
        query=query.query,
        location=query.location,
        found=result.found,
        new=result.new,
        duplicates=result.duplicates,
        stored=result.stored,
    )

    print()
    print("=" * 80)
    print("Autlead Acquisition Import")
    print("=" * 80)

    print()
    print(f"Results file:       {args.results_file}")
    print(f"Query:              {query.query}")
    print(f"Location:           {query.location}")
    print(f"Limit:              {query.limit}")

    print()
    print("Results")
    print(f"  Found:            {result.found}")
    print(f"  New:              {result.new}")
    print(f"  Duplicates:       {result.duplicates}")
    print(f"  Stored:           {result.stored}")
    print()