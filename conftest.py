import os

import pytest
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

load_dotenv()
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]


from app.core import settings  # noqa: E402
from app.db import get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def apply_migrations():
    """
    Build the schema once for the whole run, then tear it down.

    Sync on purpose: Alembic's async env.py calls `asyncio.run()`
    """
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")

    command.upgrade(cfg, "head")

    yield

    command.downgrade(cfg, "base")


@pytest.fixture(scope="session")
def engine():
    """One engine for the whole run, not per test."""

    return create_async_engine(settings.DATABASE_URL, echo=False, poolclass=NullPool)


@pytest.fixture
async def db_session(engine):
    """
    A session whose writes are discarded at the end of the test.
    """

    async with engine.connect() as connection:
        transaction = await connection.begin()

        session_factory = async_sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        async with session_factory() as session:
            yield session

        await transaction.rollback()


@pytest.fixture
async def client(db_session: AsyncSession):
    """An AsyncClient wired to the app, sharing the test's session and rollback."""
    from httpx import ASGITransport, AsyncClient

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def base_user(db_session):
    """A verified, active user other tests can authenticate as or collide against."""

    from app.auth.models import UserModel

    user = UserModel(name="Yassine", email="yassine@yassinecodes.dev", is_verified=True)

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
async def authed_client(client, base_user):
    """A client whose requests resolve to `base_user`, bypassing real token checks."""

    from app.auth.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: base_user

    yield client

    app.dependency_overrides.pop(get_current_user, None)
