import argparse
import asyncio

from app.core.database.session import SessionFactory
from app.core.logging import configure_logging, get_logger
from app.models.schemas import DiscoveryQuery
from app.pipelines.common import run_business_discovery_pipeline
from app.providers.discovery import GosomGoogleMapsDiscoveryProvider


logger = get_logger(__name__)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Autlead business discovery pipeline."
    )

    parser.add_argument(
        "query",
        help="Business category or search query, e.g. dentists",
    )

    parser.add_argument(
        "location",
        help="Geographic area, e.g. Lahore, Pakistan",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of businesses to process.",
    )

    parser.add_argument(
        "--proxy",
        default=None,
        help="Optional proxy URL for Google Maps extraction.",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of extractor workers.",
    )

    parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="Disable provider enrichment.",
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
        default=5.0,
        help="Grid cell size in kilometers.",
    )

    parser.add_argument(
        "--zoom",
        type=int,
        default=15,
        help="Google Maps zoom level used for grid searches.",
    )

    args = parser.parse_args()

    query = DiscoveryQuery(
        query=args.query,
        location=args.location,
        limit=args.limit,
    )

    provider = GosomGoogleMapsDiscoveryProvider(
        proxy=args.proxy,
        concurrency=args.workers,
        depth=1,
        zoom=args.zoom,
        grid_bbox=args.grid_bbox,
        grid_cell_km=args.grid_cell_km,
    )

    async with SessionFactory() as session:
        result = await run_business_discovery_pipeline(
            provider=provider,
            query=query,
            session=session,
        )

    logger.info(
        "discovery_pipeline_completed",
        found=result.found,
        new=result.new,
        duplicates=result.duplicates,
        stored=result.stored,
    )

    print(
        f"Found: {result.found} | "
        f"New: {result.new} | "
        f"Duplicates: {result.duplicates} | "
        f"Stored: {result.stored}"
    )


if __name__ == "__main__":
    configure_logging()
    asyncio.run(main())