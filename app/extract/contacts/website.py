# app/extract/contacts/website.py
from __future__ import annotations

from collections.abc import Sequence

from app.models.schemas.crawling import WebsiteContent

from .email import extract_emails
from .hrefs import (
    extract_href_links,
    extract_mailto_links,
    extract_tel_links,
)
from app.models.schemas.contacts import ContactEvidence, ContactExtractionResult
from .phone import extract_phones
from .social import extract_social_urls


class WebsiteContactExtractor:
    """
    Extract contact information from already-crawled website pages.

    This class orchestrates the contact-specific extractors. It does not
    contain email, phone, HTML, or social parsing rules.
    """

    def extract(
        self,
        pages: Sequence[WebsiteContent],
    ) -> ContactExtractionResult:
        result = ContactExtractionResult()

        email_seen: set[str] = set()
        phone_seen: set[str] = set()
        social_seen: set[str] = set()

        for page in pages:
            self._extract_page(
                page=page,
                result=result,
                email_seen=email_seen,
                phone_seen=phone_seen,
                social_seen=social_seen,
            )

        return result

    @staticmethod
    def _extract_page(
        *,
        page: WebsiteContent,
        result: ContactExtractionResult,
        email_seen: set[str],
        phone_seen: set[str],
        social_seen: set[str],
    ) -> None:
        source_url = page.url
        text = page.text or ""
        html = page.html or ""

        # HTML → href values.
        mailto_links = extract_mailto_links(html)
        tel_links = extract_tel_links(html)
        href_links = extract_href_links(html)

        # Emails.
        for email in extract_emails(
            text=text,
            mailto_links=mailto_links,
        ):
            if email in email_seen:
                continue

            email_seen.add(email)

            result.emails.append(email)
            result.evidence.append(
                ContactEvidence(
                    value=email,
                    source_url=source_url,
                    kind="email",
                )
            )

        # Phones.
        for phone in extract_phones(
            text=text,
            tel_links=tel_links,
        ):
            from .phone import phone_identity

            identity = phone_identity(phone)

            if identity in phone_seen:
                continue

            phone_seen.add(identity)

            result.phones.append(phone)
            result.evidence.append(
                ContactEvidence(
                    value=phone,
                    source_url=source_url,
                    kind="phone",
                )
            )

        # Social URLs.
        extract_social_urls(
            urls=[
                *map(str, page.links),
                *href_links,
            ],
            source_url=source_url,
            result=result,
            seen=social_seen,
        )