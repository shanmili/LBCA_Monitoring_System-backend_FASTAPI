from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# Sync engine (for table creation)
SYNC_DATABASE_URL = os.getenv("DATABASE_URL")
sync_engine = create_engine(SYNC_DATABASE_URL, echo=True)

# Async engine (for API)
raw_url = SYNC_DATABASE_URL.replace("postgres://", "postgresql://").replace("postgresql://", "postgresql+asyncpg://")
ASYNC_DATABASE_URL = raw_url

AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()