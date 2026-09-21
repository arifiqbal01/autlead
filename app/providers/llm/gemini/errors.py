# app/providers/llm/gemini/errors.py
from app.core.exceptions import AutleadError


class GeminiProviderError(AutleadError):
    pass

class GeminiUnavailableError(GeminiProviderError):
    pass


class GeminiRateLimitedError(GeminiProviderError):
    pass


class GeminiParseError(GeminiProviderError):
    pass