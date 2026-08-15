from app.models.schemas import CompanyCandidate
from app.transform.deduplication import company_deduplication_matches


def test_company_deduplication_matches_prioritize_strong_identifiers() -> None:
    matches = company_deduplication_matches(
        CompanyCandidate(
            name="Example Digital",
            normalized_name="example digital",
            domain="example.com",
            phone="+31 20 000 0000",
            city="Amsterdam",
            country="Netherlands",
        )
    )

    assert [match.field for match in matches] == ["domain", "phone", "name_location"]
    assert matches[0].value == "example.com"


def test_company_deduplication_requires_location_for_name_match() -> None:
    matches = company_deduplication_matches(
        CompanyCandidate(
            name="Example Digital",
            normalized_name="example digital",
        )
    )

    assert matches == []
