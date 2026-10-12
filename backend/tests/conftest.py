import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.config import get_settings
from app.database import Base


@pytest.fixture(autouse=True)
def _reset_limiters():
    from app import ratelimit
    for lim in (ratelimit.login_ip_limiter, ratelimit.login_email_limiter,
                ratelimit.register_limiter, ratelimit.heavy_limiter):
        lim.reset()
    yield


@pytest.fixture
def db():
    """A session on a separate database, created empty for every test."""
    url = make_url(get_settings().database_url).set(database="codescope_test")
    engine = create_engine(url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()
