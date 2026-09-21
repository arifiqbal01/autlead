# app/bootstrap/providers.py

from app.core.config.settings import settings
from app.providers.crawling.crawl4ai_provider import (
    Crawl4AICrawlingProvider,
)
from app.providers.discovery.gosom import (
    GosomGoogleMapsDiscoveryProvider,
)
from app.providers.email.sending.resend import (
    ResendEmailSendingProvider,
)
from app.providers.email.verification import (
    MrEmailCheckerProvider,
)
from app.providers.llm.gemini.provider import (
    GeminiLLMProvider,
)
from app.providers.llm.groq.provider import (
    GroqLLMProvider,
)
from app.providers.performance.pagespeed import (
    PageSpeedProvider,
)
from app.providers.technology.wappalyzer_next import (
    WappalyzerTechnologyDetectionProvider,
)


def create_crawling_provider() -> Crawl4AICrawlingProvider:
    return Crawl4AICrawlingProvider(
        headless=True,
        concurrency=5,
    )


def create_gosom_discovery_provider(
    *,
    proxy: str | None = None,
    concurrency: int = 4,
    depth: int = 5,
    zoom: int = 16,
    grid_bbox: str | None = None,
    grid_cell_km: float = 1.0,
    timeout_seconds: int = 1800,
    pages_per_browser: int = 4,
    browser_pool_size: int = 1,
) -> GosomGoogleMapsDiscoveryProvider:
    return GosomGoogleMapsDiscoveryProvider(
        results_root=settings.discovery_results_root,
        proxy=proxy,
        concurrency=concurrency,
        depth=depth,
        zoom=zoom,
        grid_bbox=grid_bbox,
        grid_cell_km=grid_cell_km,
        timeout_seconds=timeout_seconds,
        pages_per_browser=pages_per_browser,
        browser_pool_size=browser_pool_size,
    )


def create_pagespeed_provider() -> PageSpeedProvider:
    return PageSpeedProvider(
        api_key=settings.pagespeed_api_key,
    )


def create_wappalyzer_provider() -> WappalyzerTechnologyDetectionProvider:
    return WappalyzerTechnologyDetectionProvider(
        image="autlead-wappalyzer",
        timeout_seconds=30,
    )


def create_gemini_provider() -> GeminiLLMProvider:
    return GeminiLLMProvider(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        requests_per_minute=settings.gemini_rpm,
        requests_per_day=settings.gemini_rpd,
    )


def create_groq_provider() -> GroqLLMProvider:
    return GroqLLMProvider(
        api_key=settings.groq_cloud_api_key,
        model=settings.groq_model,
        requests_per_minute=(
            settings.groq_requests_per_minute
        ),
        requests_per_day=(
            settings.groq_requests_per_day
        ),
        max_rate_limit_attempts=(
            settings.groq_max_rate_limit_attempts
        ),
    )


def create_email_verification_provider() -> MrEmailCheckerProvider:
    return MrEmailCheckerProvider(
        timeout_seconds=30.0,
        smtp_enabled=True,
        smtp_from="verify@webartsy.nl",
        smtp_helo_host="webartsy.nl",
        smtp_timeout_ms=10_000,
        detect_catch_all=True,
    )


def create_email_sending_provider() -> ResendEmailSendingProvider:
    return ResendEmailSendingProvider(
        api_key=settings.resend_api_key,
        api_url=settings.resend_api_url,
        timeout=settings.resend_timeout_seconds,
    )