from __future__ import annotations

import pytest

from app.providers.technology.wappalyzer_next import (
    WappalyzerTechnologyDetectionProvider,
)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_wappalyzer_next_detects_saved_company_website(
    company,
) -> None:
    """Run Wappalyzer against a real website saved on a Company."""

    assert company.website, "Test company has no saved website."

    website = str(company.website)

    provider = WappalyzerTechnologyDetectionProvider(
        scan_type="full",
        timeout_seconds=60,
    )

    technologies = await provider.detect(
        website,
        timeout=60,
    )

    print(f"\n{'=' * 80}")
    print(f"Company: {company.name}")
    print(f"Saved website: {website}")
    print(f"Technologies detected: {len(technologies)}")

    for technology in technologies:
        print(
            f"- {technology.name}"
            f" | version={technology.version or ''}"
            f" | confidence={technology.confidence}"
            f" | categories={technology.categories}"
            f" | groups={technology.groups}"
        )

    assert isinstance(technologies, list)

    for technology in technologies:
        assert technology.name
        assert technology.confidence is not None
        assert 0 <= technology.confidence <= 100

    print(f"{'=' * 80}")