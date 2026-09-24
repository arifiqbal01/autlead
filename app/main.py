from __future__ import annotations

import argparse
import asyncio

from app.cli import (
    build_acquisition_parser,
    build_email_send_parser,
    build_enrichment_parser,
    build_webartsy_saved_parser,
    run_acquisition,
    run_email_send,
    run_enrichment,
    run_webartsy_saved,
)
from app.core.logging import configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Autlead command-line interface.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # ---------------------------------------------------------
    # Acquisition
    # ---------------------------------------------------------

    acquisition_parser = subparsers.add_parser(
        "acquisition",
        help="Run the business acquisition pipeline.",
    )

    build_acquisition_parser(
        parser=acquisition_parser,
    )

    # ---------------------------------------------------------
    # Enrichment
    # ---------------------------------------------------------

    enrichment_parser = subparsers.add_parser(
        "enrichment",
        help=(
            "Enrich companies already stored "
            "in PostgreSQL."
        ),
    )

    build_enrichment_parser(
        parser=enrichment_parser,
    )

    # ---------------------------------------------------------
    # Saved enrichment data export
    # Temporary WebArtsy-specific export
    # ---------------------------------------------------------

    webartsy_saved_parser = subparsers.add_parser(
        "enrichment-saved",
        help=(
            "Export already-saved WebArtsy data "
            "without calling providers."
        ),
    )

    build_webartsy_saved_parser(
        parser=webartsy_saved_parser,
    )

    # ---------------------------------------------------------
    # Email
    # ---------------------------------------------------------

    email_send_parser = subparsers.add_parser(
        "email-send",
        help="Send email to eligible persisted contacts.",
    )

    build_email_send_parser(
        parser=email_send_parser,
    )

    return parser


async def async_main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "acquisition":
        await run_acquisition(args)
        return

    if args.command == "enrichment":
        await run_enrichment(args)
        return

    if args.command == "enrichment-saved":
        await run_webartsy_saved(args)
        return

    if args.command == "email-send":
        await run_email_send(args)
        return

    parser.error(
        f"Unknown command: {args.command}"
    )


def main() -> None:
    configure_logging()

    asyncio.run(
        async_main()
    )


if __name__ == "__main__":
    main()