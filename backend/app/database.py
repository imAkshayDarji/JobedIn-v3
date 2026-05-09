from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

_database_url = settings.DATABASE_URL.strip()
if not _database_url:
    raise RuntimeError(
        "DATABASE_URL is empty or whitespace-only. Remove the variable to use the "
        "development default, or set a valid Postgres URL (Railway: link Postgres)."
    )
if _database_url.startswith("postgres://"):
    _database_url = _database_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif _database_url.startswith("postgresql://") and not _database_url.startswith(
    "postgresql+"
):
    _database_url = _database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

async_engine = create_async_engine(_database_url, echo=False)
async_session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
