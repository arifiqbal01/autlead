from app.models.schemas import BusinessRecord
from app.transform.normalization import (
    normalize_business_record,
    normalize_company_name,
    normalize_domain,
    normalize_url,
)


def test_normalize_domain_removes_scheme_www_path_and_port() -> None:
    assert normalize_domain("HTTPS://WWW.Example.COM:443/path") == "example.com"


def test_normalize_url_canonicalizes_scheme_host_and_trailing_slash() -> None:
    assert normalize_url("HTTP://WWW.Example.COM/") == "https://example.com"


def test_normalize_company_name_is_deterministic() -> None:
    assert normalize_company_name("  Example   Digital LTD  ") == "example digital ltd"


def test_normalize_business_record_builds_company_candidate() -> None:
    candidate = normalize_business_record(
        BusinessRecord(
            name="  Example   Digital LTD  ",
            website="HTTPS://WWW.Example.COM/",
            phone="+31   20 000 0000",
            city=" Amsterdam ",
            country=" Netherlands ",
            address=" Main Street 1 ",
            category=" Agency ",
            source_name="Fake Directory",
            source_type="directory",
            provider_name="fake",
        )
    )

    assert candidate.name == "Example Digital LTD"
    assert candidate.normalized_name == "example digital ltd"
    assert candidate.website == "https://example.com"
    assert candidate.domain == "example.com"
    assert candidate.phone == "+31 20 000 0000"
    assert candidate.city == "Amsterdam"
    assert candidate.country == "Netherlands"
    assert candidate.address == "Main Street 1"
    assert candidate.category == "Agency"
