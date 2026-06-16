import os
import subprocess
from collections.abc import AsyncIterator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from app.config import get_settings
from app.db.session import get_db_session
from app.main import app


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as container:
        yield container


@pytest.fixture(scope="session")
def db_url(postgres_container: PostgresContainer) -> str:
    url = postgres_container.get_connection_url()
    return url.replace("psycopg2", "asyncpg")


@pytest.fixture(scope="session", autouse=True)
def run_migrations(db_url: str) -> Generator[None, None, None]:
    env = {**os.environ, "DATABASE_URL": db_url}
    subprocess.run(["uv", "run", "alembic", "downgrade", "base"], env=env, check=False)
    subprocess.run(["uv", "run", "alembic", "upgrade", "head"], env=env, check=True)
    yield
    subprocess.run(["uv", "run", "alembic", "downgrade", "base"], env=env, check=False)


@pytest_asyncio.fixture(scope="session")
async def test_engine(db_url: str):
    engine = create_async_engine(db_url, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncIterator[AsyncSession]:
    TestSession = async_sessionmaker(
        bind=test_engine, expire_on_commit=False, class_=AsyncSession
    )
    async with TestSession() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    get_settings.cache_clear()
    app.dependency_overrides[get_db_session] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
