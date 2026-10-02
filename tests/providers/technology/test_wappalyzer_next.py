from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.providers.technology.wappalyzer_next import (
    WappalyzerTechnologyDetectionProvider,
)

WEBSITE = "https://example.com/"


@pytest.mark.asyncio
async def test_detect_maps_wappalyzer_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = WappalyzerTechnologyDetectionProvider()

    output = """
    {
        "https://example.com/": {
            "WordPress": {
                "version": "6.8.2",
                "confidence": 100,
                "categories": ["CMS"],
                "groups": ["CMS"]
            },
            "Google Analytics": {
                "version": null,
                "confidence": 75,
                "categories": ["Analytics"],
                "groups": ["Analytics"]
            }
        }
    }
    """

    async def fake_run(
        command: list[str],
        *,
        container_name: str,
        timeout: int,
    ) -> str:
        assert container_name.startswith("autlead-wappalyzer-")
        assert timeout == 45

        assert command == [
            "docker",
            "run",
            "--rm",
            "--name",
            container_name,
            "--memory",
            "1g",
            "--memory-swap",
            "1g",
            "--cpus",
            "1",
            "autlead-wappalyzer",
            "-i",
            WEBSITE,
            "--scan-type",
            "full",
            "-t",
            "30",
            "-oJ",
            "-",
        ]

        return output

    monkeypatch.setattr(provider, "_run", fake_run)

    technologies = await provider.detect(WEBSITE)

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
async def test_detect_uses_custom_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = WappalyzerTechnologyDetectionProvider(
        timeout_seconds=30,
        hard_timeout_grace_seconds=15,
    )

    captured: dict[str, object] = {}

    async def fake_run(
        command: list[str],
        *,
        container_name: str,
        timeout: int,
    ) -> str:
        captured["command"] = command
        captured["container_name"] = container_name
        captured["timeout"] = timeout

        return '{"https://example.com/": {}}'

    monkeypatch.setattr(provider, "_run", fake_run)

    result = await provider.detect(
        WEBSITE,
        timeout=45,
    )

    assert result == []

    # Wappalyzer receives the requested 45-second scan timeout.
    assert "-t" in captured["command"]
    command = captured["command"]
    assert isinstance(command, list)
    assert command[command.index("-t") + 1] == "45"

    # Autlead's hard watchdog gets an additional 15 seconds.
    assert captured["timeout"] == 60


@pytest.mark.asyncio
async def test_detect_uses_provider_timeout_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = WappalyzerTechnologyDetectionProvider(
        timeout_seconds=60,
        hard_timeout_grace_seconds=15,
    )

    captured: dict[str, object] = {}

    async def fake_run(
        command: list[str],
        *,
        container_name: str,
        timeout: int,
    ) -> str:
        captured["command"] = command
        captured["container_name"] = container_name
        captured["timeout"] = timeout

        return '{"https://example.com/": {}}'

    monkeypatch.setattr(provider, "_run", fake_run)

    result = await provider.detect(WEBSITE)

    assert result == []

    command = captured["command"]
    assert isinstance(command, list)
    assert command[command.index("-t") + 1] == "60"

    # 60-second Wappalyzer timeout + 15-second watchdog grace.
    assert captured["timeout"] == 75


@pytest.mark.asyncio
async def test_detect_raises_when_wappalyzer_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = WappalyzerTechnologyDetectionProvider()

    async def fake_run(
        command: list[str],
        *,
        container_name: str,
        timeout: int,
    ) -> str:
        raise RuntimeError(
            "Wappalyzer failed with exit code 1: browser error"
        )

    monkeypatch.setattr(provider, "_run", fake_run)

    with pytest.raises(
        RuntimeError,
        match="Wappalyzer failed with exit code 1",
    ):
        await provider.detect(WEBSITE)


def test_build_command_uses_expected_arguments() -> None:
    provider = WappalyzerTechnologyDetectionProvider(
        docker_command="docker",
        image="autlead-wappalyzer",
        scan_type="full",
        timeout_seconds=30,
    )

    command = provider._build_command(
        website=WEBSITE,
        timeout=45,
        container_name="autlead-wappalyzer-test",
    )

    assert command == [
        "docker",
        "run",
        "--rm",
        "--name",
        "autlead-wappalyzer-test",
        "--memory",
        "1g",
        "--memory-swap",
        "1g",
        "--cpus",
        "1",
        "autlead-wappalyzer",
        "-i",
        WEBSITE,
        "--scan-type",
        "full",
        "-t",
        "45",
        "-oJ",
        "-",
    ]


def test_build_command_supports_custom_command() -> None:
    provider = WappalyzerTechnologyDetectionProvider(
        docker_command="custom-docker",
        image="custom-wappalyzer",
        scan_type="full",
        timeout_seconds=30,
    )

    command = provider._build_command(
        website=WEBSITE,
        timeout=30,
        container_name="autlead-wappalyzer-test",
    )

    assert command[0] == "custom-docker"
    assert "custom-wappalyzer" in command
    assert command[
        command.index("--name") + 1
    ] == "autlead-wappalyzer-test"


@pytest.mark.asyncio
async def test_run_timeout_kills_process_and_removes_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = WappalyzerTechnologyDetectionProvider()

    process = AsyncMock()
    process.returncode = None

    async def communicate_forever() -> tuple[bytes, bytes]:
        await asyncio.sleep(60)
        return b"", b""

    process.communicate.side_effect = communicate_forever

    create_process = AsyncMock(return_value=process)

    monkeypatch.setattr(
        asyncio,
        "create_subprocess_exec",
        create_process,
    )

    terminate_process = AsyncMock()
    remove_container = AsyncMock()

    monkeypatch.setattr(
        provider,
        "_terminate_process",
        terminate_process,
    )
    monkeypatch.setattr(
        provider,
        "_remove_container",
        remove_container,
    )

    with pytest.raises(asyncio.TimeoutError):
        await provider._run(
            ["docker", "run"],
            container_name="autlead-wappalyzer-timeout-test",
            timeout=0.01,
        )

    terminate_process.assert_awaited_once_with(process)
    remove_container.assert_awaited_once_with(
        "autlead-wappalyzer-timeout-test"
    )


@pytest.mark.asyncio
async def test_run_cancellation_removes_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = WappalyzerTechnologyDetectionProvider()

    process = AsyncMock()
    process.returncode = None
    process.communicate.side_effect = asyncio.CancelledError

    create_process = AsyncMock(return_value=process)

    monkeypatch.setattr(
        asyncio,
        "create_subprocess_exec",
        create_process,
    )

    terminate_process = AsyncMock()
    remove_container = AsyncMock()

    monkeypatch.setattr(
        provider,
        "_terminate_process",
        terminate_process,
    )
    monkeypatch.setattr(
        provider,
        "_remove_container",
        remove_container,
    )

    with pytest.raises(asyncio.CancelledError):
        await provider._run(
            ["docker", "run"],
            container_name="autlead-wappalyzer-cancel-test",
            timeout=45,
        )

    terminate_process.assert_awaited_once_with(process)
    remove_container.assert_awaited_once_with(
        "autlead-wappalyzer-cancel-test"
    )