import os


# Settings are read on import, so the test database has to be chosen before the app is imported.
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-for-hs256")
os.environ["POSTGRES_DB"] = os.getenv("TEST_POSTGRES_DB", "tasks_test")
os.environ["AUTO_CANCEL_ENABLED"] = "0"

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

from config import settings
from config.database import Base, engine
from main import app


async def create_test_database():
    connection = await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database="postgres",
    )
    query = "SELECT 1 FROM pg_database WHERE datname = $1"
    database_exists = await connection.fetchval(query, settings.POSTGRES_DB)
    if not database_exists:
        await connection.execute(f'CREATE DATABASE "{settings.POSTGRES_DB}"')

    await connection.close()


@pytest.fixture
async def client():
    await create_test_database()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    await engine.dispose()
