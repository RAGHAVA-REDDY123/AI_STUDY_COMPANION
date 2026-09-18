from collections.abc import AsyncGenerator
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from pgvector.asyncpg import register_vector

from app.core.config import settings

# Enforce PostgreSQL + pgvector as the ONLY supported database engine, auto-normalizing URL schemes from cloud providers (Render, Neon, Supabase)
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+asyncpg://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

if not db_url.startswith("postgresql+asyncpg://"):
    raise RuntimeError("PostgreSQL + pgvector is the only supported database. SQLite is not permitted.")

engine = create_async_engine(
    db_url,
    echo=False,
    future=True,
    pool_size=10,
    max_overflow=5,
    pool_recycle=1800,
    pool_pre_ping=True
)

@event.listens_for(engine.sync_engine, "connect")
def on_connect(dbapi_connection, connection_record):
    async def _init_vector(conn):
        try:
            await register_vector(conn)
        except Exception:
            pass
    dbapi_connection.run_async(_init_vector)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
