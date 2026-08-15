# scripts/export_leads.py
import argparse
import asyncio
from pathlib import Path

from app.core.database.session import SessionFactory
from app.load.exports import export_leads_csv


async def main() -> None:
    parser = argparse.ArgumentParser(description="Export persisted companies to a CSV lead list.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("exports/leads.csv"),
        help="CSV output path.",
    )
    args = parser.parse_args()

    async with SessionFactory() as session:
        count = await export_leads_csv(session, args.output)

    print(f"Exported {count} leads to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
