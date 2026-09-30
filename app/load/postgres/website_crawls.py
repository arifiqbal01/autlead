from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persistence.website_crawl import WebsiteCrawl
from app.models.persistence.website_crawl_link import WebsiteCrawlLink
from app.models.schemas.crawling import WebsiteContent


async def load_website_crawl(
    session: AsyncSession,
    content: WebsiteContent,
    *,
    company_id: int,
    provider_name: str,
) -> WebsiteCrawl:
    """
    Persist crawled website content and its discovered links.

    A crawl is stored as a historical crawl record. The content hash
    allows callers to determine whether the crawled content changed.
    """

    crawl = WebsiteCrawl(
        company_id=company_id,
        url=str(content.url),
        status_code=content.status_code,
        html=content.html,
        text=content.text,
        title=content.title,
        meta_description=content.meta_description,
        content_hash=_calculate_content_hash(content),
        provider_name=provider_name,
        collected_at=content.collected_at,
    )

    session.add(crawl)
    await session.flush()

    await _load_crawl_links(
        session=session,
        crawl=crawl,
        content=content,
    )

    return crawl


async def get_website_crawl_content(
    session: AsyncSession,
    crawl: WebsiteCrawl,
) -> WebsiteContent:
    """
    Reconstruct normalized website content from a persisted crawl.

    This keeps database-specific reconstruction inside the PostgreSQL
    load layer so pipelines do not need to know about crawl link
    persistence details.
    """

    result = await session.scalars(
        select(WebsiteCrawlLink.url).where(
            WebsiteCrawlLink.website_crawl_id == crawl.id,
        )
    )

    links = list(result.all())

    return WebsiteContent(
        url=crawl.url,
        status_code=crawl.status_code,
        html=crawl.html,
        text=crawl.text,
        title=crawl.title,
        meta_description=crawl.meta_description,
        links=links,
        collected_at=crawl.collected_at,
    )


async def get_last_website_crawl(
    session: AsyncSession,
    last_crawl_id: int | None,
) -> WebsiteCrawl | None:
    """
    Return the last successfully persisted website crawl.
    """

    if last_crawl_id is None:
        return None

    return await session.get(
        WebsiteCrawl,
        last_crawl_id,
    )


async def get_last_website_crawl_for_url(
    session: AsyncSession,
    *,
    company_id: int,
    url: str,
) -> WebsiteCrawl | None:
    """
    Return the most recent persisted crawl for a specific company URL.

    Used for secondary/internal page retention so recently crawled pages
    can be rehydrated without another network request.
    """

    result = await session.scalars(
        select(WebsiteCrawl)
        .where(
            WebsiteCrawl.company_id == company_id,
            WebsiteCrawl.url == url,
        )
        .order_by(
            WebsiteCrawl.collected_at.desc(),
            WebsiteCrawl.id.desc(),
        )
        .limit(1)
    )

    return result.first()


async def _load_crawl_links(
    session: AsyncSession,
    crawl: WebsiteCrawl,
    content: WebsiteContent,
) -> None:
    """Persist unique links discovered during a website crawl."""

    seen: set[str] = set()

    for link in content.links:
        url = str(link)

        if url in seen:
            continue

        seen.add(url)

        session.add(
            WebsiteCrawlLink(
                website_crawl_id=crawl.id,
                url=url,
            )
        )


def _calculate_content_hash(
    content: WebsiteContent,
) -> str | None:
    """Calculate a deterministic hash for the crawled content."""

    value = content.text or content.html

    if not value:
        return None

    return hashlib.sha256(value.encode("utf-8")).hexdigest()
