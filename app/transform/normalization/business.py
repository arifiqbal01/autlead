import re
from urllib.parse import ParseResult, urlparse, urlunparse

from app.models.schemas import BusinessRecord, CompanyCandidate


def normalize_business_record(record: BusinessRecord) -> CompanyCandidate:
    website = normalize_url(record.website)
    domain = normalize_domain(record.domain or website)

    return CompanyCandidate(
        name=clean_text(record.name) or record.name,
        normalized_name=normalize_company_name(record.name),
        website=website,
        domain=domain,
        phone=normalize_phone(record.phone),
        country=normalize_country(record.country),
        city=clean_text(record.city),
        address=clean_text(record.address),
        category=clean_text(record.category),
    )


_COUNTRY_ALIASES = {
    "nederland": "Netherlands",
    "netherlands": "Netherlands",
}


def normalize_country(value: str | None) -> str | None:
    text = clean_text(value)
    if text is None:
        return None

    return _COUNTRY_ALIASES.get(text.casefold(), text)


def normalize_company_name(value: str) -> str:
    text = clean_text(value)
    if text is None:
        return ""

    text = text.lower()
    return re.sub(r"\s+", " ", text).strip()


def normalize_url(value: str | None) -> str | None:
    text = clean_text(value)
    if text is None:
        return None

    parsed = _parse_url(text)
    host = _normalize_host(parsed.netloc)
    if not host:
        return None

    path = parsed.path.rstrip("/")
    return urlunparse(("https", host, path, "", "", ""))


def normalize_domain(value: str | None) -> str | None:
    text = clean_text(value)
    if text is None:
        return None

    parsed = _parse_url(text)
    host = parsed.netloc or parsed.path
    return _normalize_host(host)


def normalize_phone(value: str | None) -> str | None:
    text = clean_text(value)
    if text is None:
        return None

    return re.sub(r"\s+", " ", text)


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None

    text = re.sub(r"\s+", " ", value).strip()
    if not text:
        return None

    return text


def _parse_url(value: str) -> ParseResult:
    if "://" not in value:
        value = f"https://{value}"

    return urlparse(value)


def _normalize_host(value: str) -> str | None:
    host = value.strip().lower()
    if "@" in host:
        host = host.rsplit("@", 1)[-1]
    if ":" in host:
        host = host.split(":", 1)[0]
    host = host.removeprefix("www.")
    if not host:
        return None

    return host
