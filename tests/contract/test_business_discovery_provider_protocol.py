from app.models.schemas import BusinessRecord, DiscoveryQuery
from app.providers.discovery import BusinessDiscoveryProvider


class FakeBusinessDiscoveryProvider:
    async def discover(self, query: DiscoveryQuery) -> list[BusinessRecord]:
        return [
            BusinessRecord(
                name=f"{query.query} Example",
                website="https://example.com",
                domain="example.com",
                source_name="Fake Directory",
                source_type="directory",
                provider_name="fake_discovery",
                external_id="fake-1",
                raw_data={"query": query.model_dump()},
            )
        ]


async def test_business_discovery_provider_contract_returns_business_records() -> None:
    provider: BusinessDiscoveryProvider = FakeBusinessDiscoveryProvider()
    records = await provider.discover(
        DiscoveryQuery(
            query="web design agencies",
            location="Amsterdam",
            limit=1,
        )
    )

    assert len(records) == 1
    assert records[0].name == "web design agencies Example"
    assert records[0].source_name == "Fake Directory"
    assert records[0].provider_name == "fake_discovery"
