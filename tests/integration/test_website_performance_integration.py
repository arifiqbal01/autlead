from __future__ import annotations

import pytest
from sqlalchemy import select

from app.bootstrap.providers import create_pagespeed_provider
from app.load.postgres.website_performance import (
    get_latest_website_performance,
)
from app.models.persistence.website_performance import WebsitePerformance
from app.pipelines.common.website_performance import (
    run_website_performance_pipeline,
)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_pagespeed_website_performance_pipeline(
    session,
    company,
) -> None:
    """Run PageSpeed against a real website already saved for a company."""

    assert company.website, (
        "Test company does not have a saved website. "
        "Use a company fixture populated with a real website."
    )

    website = str(company.website)

    print(f"\n{'=' * 80}")
    print(f"Company: {company.name}")
    print(f"Saved website: {website}")

    provider = create_pagespeed_provider()

    result = await run_website_performance_pipeline(
        performance_provider=provider,
        seo_provider=provider,
        websites=[
            (company.id, website),
        ],
        session=session,
    )

    assert result.analyzed == 1
    assert result.failed == 0
    assert result.stored == 1

    print(f"Analyzed: {result.analyzed}")
    print(f"Failed: {result.failed}")
    print(f"Stored: {result.stored}")

    performance = await get_latest_website_performance(
        session,
        company_id=company.id,
    )

    assert performance is not None

    assert performance.company_id == company.id
    assert performance.provider_name == "pagespeed"

    assert performance.performance_score is not None
    assert performance.seo_score is not None
    assert performance.observed_at is not None

    print(f"Performance score: {performance.performance_score}")
    print(f"SEO score: {performance.seo_score}")
    print(f"Persisted performance ID: {performance.id}")

    persisted = await session.scalar(
        select(WebsitePerformance).where(
            WebsitePerformance.id == performance.id,
        )
    )

    assert persisted is not None
    assert persisted.company_id == company.id
    assert persisted.provider_name == "pagespeed"

    assert (
        persisted.performance_score
        == performance.performance_score
    )

    assert (
        persisted.seo_score
        == performance.seo_score
    )

    print(f"\n{'=' * 80}")
    print("PageSpeed website performance pipeline passed.")