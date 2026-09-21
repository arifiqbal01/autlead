import pytest

from app.state.transitions.website_crawl_status import (
    VALID_TRANSITIONS,
    WebsiteCrawlStatus,
    can_transition,
)


def test_pending_can_transition_to_running() -> None:
    assert can_transition(
        WebsiteCrawlStatus.PENDING,
        WebsiteCrawlStatus.RUNNING,
    )


@pytest.mark.parametrize(
    "new_status",
    [
        WebsiteCrawlStatus.COMPLETED,
        WebsiteCrawlStatus.FAILED,
        WebsiteCrawlStatus.RETRYING,
    ],
)
def test_pending_cannot_transition_to_invalid_states(
    new_status: WebsiteCrawlStatus,
) -> None:
    assert not can_transition(
        WebsiteCrawlStatus.PENDING,
        new_status,
    )


@pytest.mark.parametrize(
    "new_status",
    [
        WebsiteCrawlStatus.COMPLETED,
        WebsiteCrawlStatus.FAILED,
        WebsiteCrawlStatus.RETRYING,
    ],
)
def test_running_can_transition_to_valid_states(
    new_status: WebsiteCrawlStatus,
) -> None:
    assert can_transition(
        WebsiteCrawlStatus.RUNNING,
        new_status,
    )


def test_failed_can_transition_to_retrying() -> None:
    assert can_transition(
        WebsiteCrawlStatus.FAILED,
        WebsiteCrawlStatus.RETRYING,
    )


def test_retrying_can_transition_to_running() -> None:
    assert can_transition(
        WebsiteCrawlStatus.RETRYING,
        WebsiteCrawlStatus.RUNNING,
    )


def test_retrying_can_transition_to_failed() -> None:
    assert can_transition(
        WebsiteCrawlStatus.RETRYING,
        WebsiteCrawlStatus.FAILED,
    )


def test_completed_is_terminal() -> None:
    assert VALID_TRANSITIONS[WebsiteCrawlStatus.COMPLETED] == set()


@pytest.mark.parametrize(
    "new_status",
    [
        WebsiteCrawlStatus.PENDING,
        WebsiteCrawlStatus.RUNNING,
        WebsiteCrawlStatus.FAILED,
        WebsiteCrawlStatus.RETRYING,
    ],
)
def test_completed_cannot_transition(
    new_status: WebsiteCrawlStatus,
) -> None:
    assert not can_transition(
        WebsiteCrawlStatus.COMPLETED,
        new_status,
    )


@pytest.mark.parametrize(
    "new_status",
    [
        WebsiteCrawlStatus.PENDING,
        WebsiteCrawlStatus.RUNNING,
        WebsiteCrawlStatus.FAILED,
        WebsiteCrawlStatus.RETRYING,
    ],
)
def test_completed_cannot_transition(
    new_status: WebsiteCrawlStatus,
) -> None:
    assert not can_transition(
        WebsiteCrawlStatus.COMPLETED,
        new_status,
    )


@pytest.mark.parametrize(
    "current_status,new_status",
    [
        (
            WebsiteCrawlStatus.COMPLETED,
            WebsiteCrawlStatus.RUNNING,
        ),
        (
            WebsiteCrawlStatus.COMPLETED,
            WebsiteCrawlStatus.FAILED,
        ),
        (
            WebsiteCrawlStatus.COMPLETED,
            WebsiteCrawlStatus.RETRYING,
        ),
        (
            WebsiteCrawlStatus.FAILED,
            WebsiteCrawlStatus.RUNNING,
        ),
        (
            WebsiteCrawlStatus.PENDING,
            WebsiteCrawlStatus.COMPLETED,
        ),
        (
            WebsiteCrawlStatus.PENDING,
            WebsiteCrawlStatus.FAILED,
        ),
        (
            WebsiteCrawlStatus.RUNNING,
            WebsiteCrawlStatus.PENDING,
        ),
    ],
)
def test_invalid_website_crawl_transitions(
    current_status: WebsiteCrawlStatus,
    new_status: WebsiteCrawlStatus,
) -> None:
    assert not can_transition(current_status, new_status)