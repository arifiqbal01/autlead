from typing import Protocol

from app.models.schemas import BusinessRecord, DiscoveryQuery


class BusinessDiscoveryProvider(Protocol):
    async def discover(self, query: DiscoveryQuery) -> list[BusinessRecord]:
        """Discover businesses matching an Autlead discovery query."""
        ...
