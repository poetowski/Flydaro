from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Separate engine over the direct/unpooled connection string, used by the
# worker's long-lived process (see Neon pooling risk noted in the plan).
direct_engine = create_async_engine(settings.database_url_direct, pool_pre_ping=True)
DirectSessionLocal = async_sessionmaker(direct_engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
