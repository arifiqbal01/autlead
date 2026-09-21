from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.load.postgres.website_crawls import load_website_crawl
from app.models.persistence.company import Company
from app.models.persistence.website_crawl import WebsiteCrawl
from app.models.persistence.website_crawl_link import WebsiteCrawlLink
from app.models.schemas.crawling import WebsiteContent


@pytest.fixture
def website_content() -> WebsiteContent:
    return WebsiteContent(
        url="https://example.com/",
        status_code=200,
        html="<html><body><h1>Example Company</h1></body></html>",
        text="# Example Company",
        title="Example Company",
        meta_description="Example company website.",
        links=[
            "https://example.com/about/",
            "https://example.com/contact/",
        ],
        collected_at=datetime.now(UTC),
    )


@pytest.fixture
async def company(
    session: AsyncSession,
) -> Company:
    company = Company(
        name="Example Company",
        normalized_name="example company",
        website="https://example.com/",
        domain="example.com",
        country="Pakistan",
        city="Lahore",
        category="Software company",
    )

    session.add(company)
    await session.flush()

    return company


@pytest.mark.asyncio
async def test_load_website_crawl(
    session: AsyncSession,
    company: Company,
    website_content: WebsiteContent,
) -> None:
    crawl = await load_website_crawl(
        session=session,
        content=website_content,
        company_id=company.id,
        provider_name="crawl4ai",
    )

    assert crawl.id is not None
    assert crawl.company_id == company.id
    assert crawl.url == str(website_content.url)
    assert crawl.status_code == 200
    assert crawl.html == website_content.html
    assert crawl.text == website_content.text
    assert crawl.title == website_content.title
    assert crawl.meta_description == website_content.meta_description
    assert crawl.provider_name == "crawl4ai"
    assert crawl.collected_at == website_content.collected_at

    assert crawl.content_hash is not None
    assert len(crawl.content_hash) == 64


@pytest.mark.asyncio
async def test_load_website_crawl_saves_links(
    session: AsyncSession,
    company: Company,
    website_content: WebsiteContent,
) -> None:
    crawl = await load_website_crawl(
        session=session,
        content=website_content,
        company_id=company.id,
        provider_name="crawl4ai",
    )

    statement = select(WebsiteCrawlLink).where(
        WebsiteCrawlLink.website_crawl_id == crawl.id,
    )

    links = list((await session.scalars(statement)).all())

    assert len(links) == 2

    urls = {link.url for link in links}

    assert urls == {
        "https://example.com/about/",
        "https://example.com/contact/",
    }


@pytest.mark.asyncio
async def test_load_website_crawl_calculates_content_hash(
    session: AsyncSession,
    company: Company,
    website_content: WebsiteContent,
) -> None:
    crawl = await load_website_crawl(
        session=session,
        content=website_content,
        company_id=company.id,
        provider_name="crawl4ai",
    )

    assert crawl.content_hash is not None
    assert len(crawl.content_hash) == 64
    assert all(
        character in "0123456789abcdef"
        for character in crawl.content_hash
    )


@pytest.mark.asyncio
async def test_load_website_crawl_allows_empty_links(
    session: AsyncSession,
    company: Company,
) -> None:
    content = WebsiteContent(
        url="https://example.com/",
        status_code=200,
        html="<html><body>Example</body></html>",
        text="Example",
        title="Example",
        meta_description=None,
        links=[],
        collected_at=datetime.now(UTC),
    )

    crawl = await load_website_crawl(
        session=session,
        content=content,
        company_id=company.id,
        provider_name="crawl4ai",
    )

    assert crawl.id is not None

    statement = select(WebsiteCrawlLink).where(
        WebsiteCrawlLink.website_crawl_id == crawl.id,
    )

    links = list((await session.scalars(statement)).all())

    assert links == []


@pytest.mark.asyncio
async def test_load_website_crawl_allows_empty_content(
    session: AsyncSession,
    company: Company,
) -> None:
    content = WebsiteContent(
        url="https://example.com/",
        status_code=500,
        html=None,
        text=None,
        title=None,
        meta_description=None,
        links=[],
        collected_at=datetime.now(UTC),
    )

    crawl = await load_website_crawl(
        session=session,
        content=content,
        company_id=company.id,
        provider_name="crawl4ai",
    )

    assert crawl.id is not None
    assert crawl.status_code == 500
    assert crawl.html is None
    assert crawl.text is None
    assert crawl.title is None
    assert crawl.meta_description is None
    assert crawl.content_hash is None


@pytest.mark.asyncio
async def test_load_website_crawl_deduplicates_links(session):
    content = WebsiteContent(
        url="https://example.com/",
        status_code=200,
        html="<html></html>",
        text="Example",
        title="Example",
        meta_description="Example",
        links=[
            "https://example.com/",
            "https://example.com/about/",
            "https://example.com/",
            "https://example.com/contact/",
            "https://example.com/about/",
        ],
        collected_at=datetime.now(UTC),
    )

    crawl = await load_website_crawl(
        session=session,
        content=content,
        company_id=1,
        provider_name="crawl4ai",
    )

    await session.commit()

    links = list(
        (
            await session.scalars(
                select(WebsiteCrawlLink.url).where(
                    WebsiteCrawlLink.website_crawl_id == crawl.id,
                )
            )
        ).all()
    )

    assert links == [
        "https://example.com/",
        "https://example.com/about/",
        "https://example.com/contact/",
    ]