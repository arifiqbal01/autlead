from enum import StrEnum


class WebsiteCrawlStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


VALID_TRANSITIONS: dict[
    WebsiteCrawlStatus,
    set[WebsiteCrawlStatus],
] = {
    WebsiteCrawlStatus.PENDING: {
        WebsiteCrawlStatus.RUNNING,
    },

    WebsiteCrawlStatus.RUNNING: {
        WebsiteCrawlStatus.COMPLETED,
        WebsiteCrawlStatus.FAILED,
        WebsiteCrawlStatus.RETRYING,
    },

    # A FAILED state means the previous crawl attempt failed.
    #
    # The company worker may retry the complete company operation,
    # which starts the website crawl again directly.
    WebsiteCrawlStatus.FAILED: {
        WebsiteCrawlStatus.RUNNING,
        WebsiteCrawlStatus.RETRYING,
    },

    WebsiteCrawlStatus.RETRYING: {
        WebsiteCrawlStatus.RUNNING,
        WebsiteCrawlStatus.FAILED,
    },

    # A COMPLETED crawl may become stale after the retention
    # period expires. In that case, a new crawl starts directly.
    WebsiteCrawlStatus.COMPLETED: {
        WebsiteCrawlStatus.RUNNING,
    },
}


def can_transition(
    current: WebsiteCrawlStatus,
    new: WebsiteCrawlStatus,
) -> bool:
    return new in VALID_TRANSITIONS[current]