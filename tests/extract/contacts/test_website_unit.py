from __future__ import annotations

from datetime import UTC, datetime

from app.extract.contacts import WebsiteContactExtractor
from app.models.schemas.crawling import WebsiteContent
from pydantic import TypeAdapter
from pydantic import HttpUrl

def test_extract_contacts_from_website_content() -> None:
    """Extract emails, phones, and social profiles from crawled content."""

    content = WebsiteContent(
        url="https://example.com/contact",
        status_code=200,
        html="""
        <html>
            <body>
                <h1>Contact Us</h1>

                <p>Email: hello@example.com</p>
                <p>Sales: sales@example.com</p>
                <p>Phone: +92 300 1234567</p>

                <a href="mailto:info@example.com">
                    Email us
                </a>

                <a href="tel:+923001234567">
                    Call us
                </a>

                <a href="https://www.linkedin.com/company/example/">
                    LinkedIn
                </a>

                <a href="https://www.linkedin.com/in/john-smith/">
                    John Smith
                </a>

                <a href="https://www.facebook.com/example">
                    Facebook
                </a>

                <a href="https://www.instagram.com/example/">
                    Instagram
                </a>
            </body>
        </html>
        """,
        text="""
        Contact Us

        Email: hello@example.com
        Sales: sales@example.com

        Phone: +92 300 1234567
        """,
        title="Contact Us",
        meta_description="Contact Example",
        links=TypeAdapter(list[HttpUrl]).validate_python(
            [
                "https://www.linkedin.com/company/example/",
                "https://www.linkedin.com/in/john-smith/",
                "https://www.facebook.com/example",
                "https://www.instagram.com/example/",
            ]
        ),
        collected_at=datetime.now(UTC),
    )

    extractor = WebsiteContactExtractor()

    result = extractor.extract([content])

    assert "hello@example.com" in result.emails
    assert "sales@example.com" in result.emails
    assert "info@example.com" in result.emails

    assert "+923001234567" in result.phones

    assert any(
        "linkedin.com/company/example" in str(url)
        for url in result.linkedin_company_urls
    )

    assert any(
        "linkedin.com/in/john-smith" in str(url)
        for url in result.linkedin_profile_urls
    )

    assert any(
        "facebook.com/example" in str(url)
        for url in result.facebook_urls
    )

    assert any(
        "instagram.com/example" in str(url)
        for url in result.instagram_urls
    )

    assert result.evidence