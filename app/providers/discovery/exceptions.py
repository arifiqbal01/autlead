from app.core.exceptions import AutleadError


class BusinessDiscoveryProviderError(AutleadError):
    """Raised when a business discovery provider cannot satisfy a query."""
