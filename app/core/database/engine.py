from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config.settings import settings

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_pre_ping=True,
)