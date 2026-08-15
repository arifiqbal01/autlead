import csv
from datetime import UTC, datetime

from app.load.exports import LEAD_EXPORT_FIELDS, LeadExportRow, write_lead_rows_csv


def test_write_lead_rows_csv_writes_expected_header_and_rows(tmp_path) -> None:
    output_path = tmp_path / "exports" / "leads.csv"

    write_lead_rows_csv(
        [
            LeadExportRow(
                company_name="Example Digital",
                website="https://example.com",
                domain="example.com",
                phone="+31 20 000 0000",
                city="Amsterdam",
                country="Netherlands",
                address="Main Street 1",
                category="Agency",
                source="Google Maps",
                created_at=datetime(2026, 8, 14, 12, 0, tzinfo=UTC),
            ),
            LeadExportRow(
                company_name="No Website Company",
                created_at=datetime(2026, 8, 14, 13, 0, tzinfo=UTC),
            ),
        ],
        output_path,
    )

    with output_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert rows[0] == {
        "company_name": "Example Digital",
        "website": "https://example.com",
        "domain": "example.com",
        "phone": "+31 20 000 0000",
        "city": "Amsterdam",
        "country": "Netherlands",
        "address": "Main Street 1",
        "category": "Agency",
        "source": "Google Maps",
        "created_at": "2026-08-14T12:00:00Z",
    }
    assert rows[1]["company_name"] == "No Website Company"
    assert rows[1]["website"] == ""
    assert rows[1]["source"] == ""
    assert list(rows[0].keys()) == LEAD_EXPORT_FIELDS
