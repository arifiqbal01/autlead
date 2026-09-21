from app.core.exceptions import AutleadError


class GroqProviderError(AutleadError):
    pass


class GroqUnavailableError(GroqProviderError):
    pass


class GroqRateLimitedError(GroqProviderError):
    pass


class GroqParseError(GroqProviderError):
    pass