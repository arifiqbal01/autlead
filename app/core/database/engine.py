from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config.settings import settings


engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)