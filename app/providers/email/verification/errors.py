from app.core.exceptions.base import AutleadError


class MrEmailCheckerError(AutleadError):
    """Base mr-outreach-checker provider error."""


class MrEmailCheckerTimeoutError(
    MrEmailCheckerError
):
    """The Node verification process timed out."""


class MrEmailCheckerParseError(
    MrEmailCheckerError
):
    """The Node process returned an invalid response."""