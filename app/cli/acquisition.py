from __future__ import annotations

import argparse

from app.bootstrap.providers import (
    create_gosom_discovery_provider,
)
from app.core.logging import get_logger
from app.pipelines.acquisition.models import (
    DiscoveryQuery,
)
from app.pipelines.acquisition.pipeline import (
    run_acquisition_pipeline,
)

logger = get_logger(__name__)


def build_parser(
    parser: argparse.ArgumentParser | None = None,
) -> argparse.ArgumentParser:
    if parser is None:
        parser = argparse.ArgumentParser(
            description="Run the Autlead acquisition pipeline.",
        )

    parser.add_argument(
        "query",
        help="Business category or search query, e.g. dentists",
    )

    parser.add_argument(
        "location",
        help="Geographic area, e.g. Amsterdam, Nederland",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of businesses to return after deduplication.",
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

    return parser


async def run(args: argparse.Namespace) -> None:
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
        query=args.query,
        location=args.location,
        limit=args.limit,
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
    print(f"Query:              {args.query}")
    print(f"Location:           {args.location}")
    print(f"Limit:              {args.limit}")
    print(f"Workers:            {args.workers}")
    print(f"Depth:              {args.depth}")
    print(f"Discovery timeout:  {args.discovery_timeout}s")

    if args.grid_bbox:
        print(f"Grid bbox:          {args.grid_bbox}")
        print(f"Grid cell:          {args.grid_cell_km} km")
        print(f"Zoom:               {args.zoom}")

    print()
    print("Results")
    print(f"  Found:            {result.found}")
    print(f"  New:              {result.new}")
    print(f"  Duplicates:       {result.duplicates}")
    print(f"  Stored:           {result.stored}")

    print()