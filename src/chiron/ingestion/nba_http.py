import logging
import time
from collections.abc import Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

_IMPERSONATE_PROFILES = ("chrome120", "chrome", "chrome110")
_NBA_WARMUP_URL = "https://www.nba.com/stats/"


def _make_impersonated_session():
    from curl_cffi import requests as cr

    last_exc: Exception | None = None
    for profile in _IMPERSONATE_PROFILES:
        try:
            session = cr.Session(impersonate=profile)
            session.get(_NBA_WARMUP_URL, timeout=20)
            logger.info("NBA HTTP warmup succeeded with impersonate=%s", profile)
            return session
        except Exception as exc:
            last_exc = exc
            logger.warning("NBA HTTP impersonate=%s failed: %s", profile, exc)
    raise RuntimeError("Unable to create impersonated NBA HTTP session") from last_exc


def configure_nba_http() -> str:
    """Point nba_api at a browser-like TLS session so cloud IPs are not blocked."""
    from nba_api.library.http import NBAHTTP
    from nba_api.stats.library.http import NBAStatsHTTP

    try:
        session = _make_impersonated_session()
    except Exception as exc:
        logger.warning("Falling back to default nba_api session: %s", exc)
        return "requests"

    NBAHTTP.set_session(session)
    NBAStatsHTTP.set_session(session)
    return "curl_cffi"


def reset_nba_session() -> None:
    """Drop the cached nba_api session so the next call opens a fresh connection."""
    from nba_api.library.http import NBAHTTP
    from nba_api.stats.library.http import NBAStatsHTTP

    for cls in (NBAStatsHTTP, NBAHTTP):
        session = getattr(cls, "_session", None)
        if session is not None:
            try:
                session.close()
            except Exception:
                logger.debug("Failed to close NBA HTTP session", exc_info=True)
            cls.set_session(None)

    try:
        configure_nba_http()
    except Exception:
        logger.warning("Failed to rebuild NBA HTTP session", exc_info=True)


def with_retry(fn: Callable[[], T], *, attempts: int = 4, delay: float = 1.5) -> T:
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            logger.warning("NBA API attempt %s/%s failed: %s", attempt, attempts, exc)
            if attempt < attempts:
                reset_nba_session()
                time.sleep(delay * attempt)
    assert last_exc is not None
    raise last_exc
