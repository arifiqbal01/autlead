from __future__ import annotations

import pytest

from app.providers.technology.wappalyzer_next import (
    WappalyzerTechnologyDetectionProvider,
)


@pytest.mark.asyncio
async def test_detect_maps_wappalyzer_results() -> None:
    provider = WappalyzerTechnologyDetectionProvider()

    output = """
    {
        "https://example.com/": {
            "WordPress": {
                "version": "6.8.2",
                "confidence": 100,
                "categories": [
                    "CMS"
                ],
                "groups": [
                    "CMS"
                ]
            },
            "Google Analytics": {
                "version": null,
                "confidence": 75,
                "categories": [
                    "Analytics"
                ],
                "groups": [
                    "Analytics"
                ]
            }
        }
    }
    """

    async def fake_run(
        command: list[str],
        *,
        timeout: int,
    ) -> str:
        assert command == [
            "wappalyzer",
            "-i",
            "https://example.com/",
            "--scan-type",
            "full",
            "-t",
            "30",
            "-oJ",
            "-",
        ]
        assert timeout == 30

        return output

    provider._run = fake_run  # type: ignore[method-assign]

    technologies = await provider.detect(
        "https://example.com/",
    )

    assert len(technologies) == 2

    wordpress = technologies[0]

    assert wordpress.name == "WordPress"
    assert wordpress.version == "6.8.2"
    assert wordpress.confidence == 100
    assert wordpress.categories == ["CMS"]
    assert wordpress.groups == ["CMS"]

    analytics = technologies[1]

    assert analytics.name == "Google Analytics"
    assert analytics.version is None
    assert analytics.confidence == 75
    assert analytics.categories == ["Analytics"]
    assert analytics.groups == ["Analytics"]


@pytest.mark.asyncio
async def test_detect_uses_custom_timeout() -> None:
    provider = WappalyzerTechnologyDetectionProvider(
        timeout_seconds=30,
    )

    captured: dict[str, object] = {}

    async def fake_run(
        command: list[str],
        *,
        timeout: int,
    ) -> str:
        captured["command"] = command
        captured["timeout"] = timeout

        return '{"https://example.com/": {}}'

    provider._run = fake_run  # type: ignore[method-assign]

    result = await provider.detect(
        "https://example.com/",
        timeout=45,
    )

    assert result == []

    assert captured["timeout"] == 45
    assert captured["command"] == [
        "wappalyzer",
        "-i",
        "https://example.com/",
        "--scan-type",
        "full",
        "-t",
        "45",
        "-oJ",
        "-",
    ]


@pytest.mark.asyncio
async def test_detect_uses_provider_timeout_by_default() -> None:
    provider = WappalyzerTechnologyDetectionProvider(
        timeout_seconds=60,
    )

    captured: dict[str, object] = {}

    async def fake_run(
        command: list[str],
        *,
        timeout: int,
    ) -> str:
        captured["command"] = command
        captured["timeout"] = timeout

        return '{"https://example.com/": {}}'

    provider._run = fake_run  # type: ignore[method-assign]

    result = await provider.detect(
        "https://example.com/",
    )

    assert result == []

    assert captured["timeout"] == 60
    assert captured["command"] == [
        "wappalyzer",
        "-i",
        "https://example.com/",
        "--scan-type",
        "full",
        "-t",
        "60",
        "-oJ",
        "-",
    ]


@pytest.mark.asyncio
async def test_detect_raises_when_wappalyzer_fails() -> None:
    provider = WappalyzerTechnologyDetectionProvider()

    async def fake_run(
        command: list[str],
        *,
        timeout: int,
    ) -> str:
        raise RuntimeError(
            "Wappalyzer failed with exit code 1: browser error"
        )

    provider._run = fake_run  # type: ignore[method-assign]

    with pytest.raises(
        RuntimeError,
        match="Wappalyzer failed with exit code 1",
    ):
        await provider.detect(
            "https://example.com/",
        )


def test_build_command_uses_expected_arguments() -> None:
    provider = WappalyzerTechnologyDetectionProvider(
        wappalyzer_command="wappalyzer",
        scan_type="full",
        timeout_seconds=30,
    )

    command = provider._build_command(
        website="https://example.com/",
        timeout=45,
    )

    assert command == [
        "wappalyzer",
        "-i",
        "https://example.com/",
        "--scan-type",
        "full",
        "-t",
        "45",
        "-oJ",
        "-",
    ]


def test_build_command_supports_custom_command() -> None:
    provider = WappalyzerTechnologyDetectionProvider(
        wappalyzer_command="docker-wappalyzer",
        scan_type="full",
        timeout_seconds=30,
    )

    command = provider._build_command(
        website="https://example.com/",
        timeout=30,
    )

    assert command[0] == "docker-wappalyzer"