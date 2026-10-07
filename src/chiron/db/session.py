from collections.abc import Generator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from chiron.config import get_settings

_engine = None
_SessionLocal = None

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "postgres", "::1"}


def normalize_database_url(url: str) -> str:
    """Accept Render-style postgres:// URLs and require SSL off localhost."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in _LOCAL_HOSTS:
        return url
    query = parse_qs(parsed.query)
    if "sslmode" not in query:
        query["sslmode"] = ["require"]
        parsed = parsed._replace(query=urlencode(query, doseq=True))
        url = urlunparse(parsed)
    return url


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(normalize_database_url(settings.database_url), pool_pre_ping=True)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
