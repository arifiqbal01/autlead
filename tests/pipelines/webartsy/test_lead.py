# tests/pipelines/webartsy/test_lead.py

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.pipelines.common.business_discovery import (
    BusinessDiscoveryPipelineResult,
    DiscoveredCompany,
)
from app.pipelines.common.technology_detection import (
    WebsiteTechnologyPipelineResult,
)
from app.pipelines.common.website_performance import (
    WebsitePerformancePipelineResult,
)
from app.pipelines.webartsy.company import (
    WebArtsyCompanyResult,
    WebArtsyCompanyWorkItem,
)
from app.pipelines.webartsy.lead import (
    WebArtsyLeadResult,
    run_webartsy_lead_pipeline,
)


class FakeDiscoveryProvider:
    pass


class FakeCrawlerProvider:
    provider_name = "crawl4ai"


class FakeTechnologyProvider:
    provider_name = "fake-technology"


class FakePerformanceProvider:
    provider_name = "fake-performance"


class FakeSeoProvider:
    provider_name = "fake-seo"


@pytest.mark.asyncio
async def test_run_webartsy_lead_pipeline_orchestrates_company_workers(
    session,
) -> None:
    discovered_company = DiscoveredCompany(
        company_id=123,
        name="Example Company",
        website="https://example.com/",
    )

    discovery_result = BusinessDiscoveryPipelineResult(
        found=1,
        new=1,
        duplicates=0,
        stored=1,
        companies=[
            discovered_company,
        ],
    )

    technology_result = WebsiteTechnologyPipelineResult(
        detected=2,
        failed=0,
        stored=2,
    )

    performance_result = WebsitePerformancePipelineResult(
        analyzed=1,
        failed=0,
        stored=1,
    )

    company_result = WebArtsyCompanyResult(
        company_id=123,
        company_name="Example Company",
        website="https://example.com/",
        website_missing=False,
        technology=technology_result,
        performance=performance_result,
        website_analysis=None,
        contacts=None,
        people_analysis=None,
        pages_processed=3,
    )

    discovery_provider = FakeDiscoveryProvider()
    crawler_provider = FakeCrawlerProvider()
    technology_provider = FakeTechnologyProvider()
    performance_provider = FakePerformanceProvider()
    seo_provider = FakeSeoProvider()

    query = SimpleNamespace(
        query="web agencies",
        location="Amsterdam",
        limit=10,
    )

    with (
        patch(
            "app.pipelines.webartsy.lead.run_business_discovery_pipeline",
            new_callable=AsyncMock,
            return_value=discovery_result,
        ) as mock_discovery,
        patch(
            "app.pipelines.webartsy.lead.process_company_with_session",
            new_callable=AsyncMock,
            return_value=company_result,
        ) as mock_process_company,
    ):
        result = await run_webartsy_lead_pipeline(
            session=session,
            discovery_provider=discovery_provider,
            query=query,
            crawler_provider=crawler_provider,
            technology_provider=technology_provider,
            performance_provider=performance_provider,
            seo_provider=seo_provider,
            phone_region="NL",
            source_id=10,
            retention_days=30,
            timeout=30,
            decision_maker_limit=5,
            business_page_limit=4,
            company_workers=2,
            company_queue_size=5,
            company_retries=1,
            language="nl",
        )

    # ---------------------------------------------------------
    # Result
    # ---------------------------------------------------------

    assert isinstance(
        result,
        WebArtsyLeadResult,
    )

    assert result.discovery == discovery_result

    assert result.companies == [
        company_result,
    ]

    assert result.failures == []

    # ---------------------------------------------------------
    # Company counts
    # ---------------------------------------------------------

    assert result.companies_analyzed == 1
    assert result.companies_failed == 0

    assert result.companies_with_website == 1
    assert result.companies_without_website == 0

    assert result.people_found == 0
    assert result.decision_makers_found == 0

    # ---------------------------------------------------------
    # Technology aggregation
    # ---------------------------------------------------------

    assert result.technology.detected == 2
    assert result.technology.failed == 0
    assert result.technology.stored == 2

    # ---------------------------------------------------------
    # Performance aggregation
    # ---------------------------------------------------------

    assert result.performance.analyzed == 1
    assert result.performance.failed == 0
    assert result.performance.stored == 1

    # ---------------------------------------------------------
    # Discovery
    # ---------------------------------------------------------

    mock_discovery.assert_awaited_once_with(
        provider=discovery_provider,
        query=query,
        session=session,
    )

    # ---------------------------------------------------------
    # Company worker
    #
    # Discovery objects must be converted into neutral
    # WebArtsyCompanyWorkItem objects.
    # ---------------------------------------------------------

    mock_process_company.assert_awaited_once()

    process_kwargs = (
        mock_process_company.await_args.kwargs
    )

    processed_company = (
        process_kwargs["company"]
    )

    assert isinstance(
        processed_company,
        WebArtsyCompanyWorkItem,
    )

    assert processed_company.company_id == 123
    assert processed_company.name == "Example Company"

    assert (
        processed_company.website
        == "https://example.com/"
    )

    # ---------------------------------------------------------
    # Worker parameters
    # ---------------------------------------------------------

    assert (
        process_kwargs["crawler_provider"]
        is crawler_provider
    )

    assert (
        process_kwargs["technology_provider"]
        is technology_provider
    )

    assert (
        process_kwargs["performance_provider"]
        is performance_provider
    )

    assert (
        process_kwargs["seo_provider"]
        is seo_provider
    )

    assert process_kwargs["phone_region"] == "NL"
    assert process_kwargs["source_id"] == 10
    assert process_kwargs["retention_days"] == 30
    assert process_kwargs["timeout"] == 30
    assert process_kwargs["decision_maker_limit"] == 5
    assert process_kwargs["business_page_limit"] == 4
    assert process_kwargs["language"] == "nl"

    # The discovery/orchestration session must NOT be passed
    # into process_company_with_session().
    assert "session" not in process_kwargs


@pytest.mark.asyncio
async def test_run_webartsy_lead_pipeline_keeps_company_without_website(
    session,
) -> None:
    discovered_company = DiscoveredCompany(
        company_id=321,
        name="No Website Company",
        website=None,
    )

    discovery_result = BusinessDiscoveryPipelineResult(
        found=1,
        new=1,
        duplicates=0,
        stored=1,
        companies=[
            discovered_company,
        ],
    )

    company_result = WebArtsyCompanyResult(
        company_id=321,
        company_name="No Website Company",
        website=None,
        website_missing=True,
        technology=None,
        performance=None,
        website_analysis=None,
        contacts=None,
        people_analysis=None,
        pages_processed=0,
    )

    discovery_provider = FakeDiscoveryProvider()
    crawler_provider = FakeCrawlerProvider()
    technology_provider = FakeTechnologyProvider()
    performance_provider = FakePerformanceProvider()
    seo_provider = FakeSeoProvider()

    query = SimpleNamespace(
        query="local businesses",
        location="Amsterdam",
        limit=10,
    )

    with (
        patch(
            "app.pipelines.webartsy.lead.run_business_discovery_pipeline",
            new_callable=AsyncMock,
            return_value=discovery_result,
        ),
        patch(
            "app.pipelines.webartsy.lead.process_company_with_session",
            new_callable=AsyncMock,
            return_value=company_result,
        ) as mock_process_company,
    ):
        result = await run_webartsy_lead_pipeline(
            session=session,
            discovery_provider=discovery_provider,
            query=query,
            crawler_provider=crawler_provider,
            technology_provider=technology_provider,
            performance_provider=performance_provider,
            seo_provider=seo_provider,
            company_workers=1,
        )

    # ---------------------------------------------------------
    # Missing website is NOT a failure.
    # ---------------------------------------------------------

    assert result.companies_analyzed == 1
    assert result.companies_failed == 0

    assert result.companies_with_website == 0
    assert result.companies_without_website == 1

    assert result.companies == [
        company_result,
    ]

    assert result.failures == []

    # ---------------------------------------------------------
    # Website-dependent aggregates contribute zero.
    # ---------------------------------------------------------

    assert result.technology.detected == 0
    assert result.technology.failed == 0
    assert result.technology.stored == 0

    assert result.performance.analyzed == 0
    assert result.performance.failed == 0
    assert result.performance.stored == 0

    # ---------------------------------------------------------
    # Company without website still enters worker pool.
    # ---------------------------------------------------------

    mock_process_company.assert_awaited_once()

    process_kwargs = (
        mock_process_company.await_args.kwargs
    )

    processed_company = (
        process_kwargs["company"]
    )

    assert isinstance(
        processed_company,
        WebArtsyCompanyWorkItem,
    )

    assert processed_company.company_id == 321
    assert processed_company.name == "No Website Company"
    assert processed_company.website is None


@pytest.mark.asyncio
async def test_run_webartsy_lead_pipeline_converts_all_discovered_companies_to_work_items(
    session,
) -> None:
    first = DiscoveredCompany(
        company_id=1,
        name="First Company",
        website="https://first.example/",
    )

    second = DiscoveredCompany(
        company_id=2,
        name="Second Company",
        website=None,
    )

    discovery_result = BusinessDiscoveryPipelineResult(
        found=2,
        new=2,
        duplicates=0,
        stored=2,
        companies=[
            first,
            second,
        ],
    )

    first_result = WebArtsyCompanyResult(
        company_id=1,
        company_name="First Company",
        website="https://first.example/",
        website_missing=False,
        technology=None,
        performance=None,
        website_analysis=None,
        contacts=None,
        people_analysis=None,
        pages_processed=0,
    )

    second_result = WebArtsyCompanyResult(
        company_id=2,
        company_name="Second Company",
        website=None,
        website_missing=True,
        technology=None,
        performance=None,
        website_analysis=None,
        contacts=None,
        people_analysis=None,
        pages_processed=0,
    )

    discovery_provider = FakeDiscoveryProvider()
    crawler_provider = FakeCrawlerProvider()
    technology_provider = FakeTechnologyProvider()
    performance_provider = FakePerformanceProvider()
    seo_provider = FakeSeoProvider()

    query = SimpleNamespace(
        query="companies",
        location="Amsterdam",
        limit=2,
    )

    async def fake_process_company(
        **kwargs,
    ):
        company = kwargs["company"]

        if company.company_id == 1:
            return first_result

        return second_result

    with (
        patch(
            "app.pipelines.webartsy.lead.run_business_discovery_pipeline",
            new_callable=AsyncMock,
            return_value=discovery_result,
        ),
        patch(
            "app.pipelines.webartsy.lead.process_company_with_session",
            new_callable=AsyncMock,
            side_effect=fake_process_company,
        ) as mock_process_company,
    ):
        result = await run_webartsy_lead_pipeline(
            session=session,
            discovery_provider=discovery_provider,
            query=query,
            crawler_provider=crawler_provider,
            technology_provider=technology_provider,
            performance_provider=performance_provider,
            seo_provider=seo_provider,
            company_workers=2,
        )

    assert result.companies_analyzed == 2
    assert result.companies_failed == 0

    assert result.companies_with_website == 1
    assert result.companies_without_website == 1

    assert mock_process_company.await_count == 2

    processed_items = [
        call.kwargs["company"]
        for call in (
            mock_process_company.await_args_list
        )
    ]

    assert all(
        isinstance(
            item,
            WebArtsyCompanyWorkItem,
        )
        for item in processed_items
    )

    processed_by_id = {
        item.company_id: item
        for item in processed_items
    }

    assert processed_by_id[1].name == "First Company"

    assert (
        processed_by_id[1].website
        == "https://first.example/"
    )

    assert processed_by_id[2].name == "Second Company"
    assert processed_by_id[2].website is None