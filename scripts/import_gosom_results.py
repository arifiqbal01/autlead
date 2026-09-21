# scripts/import_gosom_results.py

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.core.database.session import SessionFactory
from app.models.schemas import DiscoveryQuery
from app.pipelines.common import (
    run_business_discovery_pipeline,
)
from app.providers.discovery.gosom_import import (
    GosomResultsFileDiscoveryProvider,
)


async def run(
    *,
    results_file: Path,
    query_text: str,
    location: str,
) -> None:
    results_file = (
        results_file
        .expanduser()
        .resolve()
    )

    if not results_file.is_file():
        raise FileNotFoundError(
            f"Results file not found: {results_file}"
        )

    query = DiscoveryQuery(
        query=query_text,
        location=location,
        limit=None,
    )

    provider = GosomResultsFileDiscoveryProvider(
        results_file=results_file,
    )

    async with SessionFactory() as session:
        result = await run_business_discovery_pipeline(
            provider=provider,
            query=query,
            session=session,
        )

    print()
    print("Gosom import completed")
    print(f"File:       {results_file}")
    print(f"Found:      {result.found}")
    print(f"New:        {result.new}")
    print(f"Duplicates: {result.duplicates}")
    print(f"Stored:     {result.stored}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Import an existing Gosom results.csv "
            "through Autlead's normal discovery pipeline."
        )
    )

    parser.add_argument(
        "results_file",
        type=Path,
        help="Path to an existing Gosom results.csv",
    )

    parser.add_argument(
        "query",
        help="Original discovery query",
    )

    parser.add_argument(
        "location",
        help="Original discovery location",
    )

    args = parser.parse_args()

    asyncio.run(
        run(
            results_file=args.results_file,
            query_text=args.query,
            location=args.location,
        )
    )


if __name__ == "__main__":
    main()