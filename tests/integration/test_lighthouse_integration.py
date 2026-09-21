from __future__ import annotations

import pytest

from app.providers.performance.lighthouse import LighthouseProvider


@pytest.mark.asyncio
@pytest.mark.integration
async def test_lighthouse_analyzes_real_website() -> None:
    """Run Lighthouse against a real website."""

    website = "https://example.com/"

    provider = LighthouseProvider(
        timeout_seconds=120,
        form_factor="mobile",
    )

    performance = await provider.analyze_performance(
        website,
    )

    seo = await provider.analyze_seo(
        website,
    )

    print(f"\n{'=' * 80}")
    print(f"Website: {website}")
    print(f"Performance score: {performance.performance_score}")
    print(f"SEO score: {seo.seo_score}")
    print(f"{'=' * 80}")

    assert performance.performance_score is not None
    assert 0 <= performance.performance_score <= 100

    assert seo.seo_score is not None
    assert 0 <= seo.seo_score <= 100