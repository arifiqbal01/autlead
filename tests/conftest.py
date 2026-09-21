import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from app.models.persistence.company import Company
from app.core.database.engine import engine


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    test_engine = create_async_engine(
        engine.url,
        poolclass=NullPool,
    )

    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session
        await session.rollback()

    await test_engine.dispose()

@pytest_asyncio.fixture
async def company(session):
    company = Company(
        name="Denhartog Zorg",
        normalized_name="denhartog-zorg",
        website="http://denhartog-zorg.nl/",
        domain="denhartog-zorg.nl",
        country="Netherlands",
        city="Arnhem",
    )

    session.add(company)
    await session.flush()

    return company