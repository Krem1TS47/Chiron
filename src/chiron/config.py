from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"


def compute_nba_season(today: date | None = None) -> str:
    """Return the latest NBA season string, e.g. 2025-26.

    Seasons start in October. Before October, use the season that just finished.
    """
    today = today or date.today()
    start_year = today.year if today.month >= 10 else today.year - 1
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def compute_espn_season(today: date | None = None) -> int:
    """Return the ESPN fantasy seasonId (season start year)."""
    today = today or date.today()
    return today.year if today.month >= 10 else today.year - 1


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://chiron:chiron@localhost:5432/chiron"
    espn_league_id: str = ""
    espn_season: int = Field(default_factory=compute_espn_season)
    espn_swid: str = ""
    espn_s2: str = ""
    nba_season: str = Field(default_factory=compute_nba_season)
    ingest_player_limit: int = 50
    model_dir: str = "models"
    min_games_for_features: int = 5
    rolling_windows: str = "5,10,15"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    artifacts_dir: str = "artifacts"

    @field_validator("nba_season", mode="before")
    @classmethod
    def _default_nba_season(cls, value: object) -> object:
        if value in (None, ""):
            return compute_nba_season()
        return value

    @field_validator("espn_season", mode="before")
    @classmethod
    def _default_espn_season(cls, value: object) -> object:
        if value in (None, ""):
            return compute_espn_season()
        return value

    @property
    def rolling_window_list(self) -> list[int]:
        return [int(w.strip()) for w in self.rolling_windows.split(",") if w.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_feature_config() -> dict:
    config_path = CONFIG_DIR / "feature_definitions.yaml"
    if not config_path.exists():
        return {}
    with config_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
