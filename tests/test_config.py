from datetime import date
from unittest.mock import patch

from chiron.config import compute_espn_season, compute_nba_season
from chiron.ingestion.nba_http import with_retry


def test_nba_season_offseason_uses_completed_year():
    assert compute_nba_season(date(2026, 8, 16)) == "2025-26"


def test_nba_season_october_starts_new_year():
    assert compute_nba_season(date(2026, 10, 15)) == "2026-27"


def test_espn_season_matches_nba_start_year():
    assert compute_espn_season(date(2026, 8, 16)) == 2025
    assert compute_espn_season(date(2026, 10, 15)) == 2026


@patch("chiron.ingestion.nba_http.reset_nba_session")
def test_with_retry_succeeds_after_transient_error(mock_reset):
    calls = {"n": 0}

    def flaky() -> int:
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("transient")
        return 42

    assert with_retry(flaky, attempts=3, delay=0) == 42
    assert calls["n"] == 2
    mock_reset.assert_called_once()
