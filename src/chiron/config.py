from functools import lru_cache
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://chiron:chiron@localhost:5432/chiron"
    espn_league_id: str = ""
    espn_season: int = 2025
    espn_swid: str = ""
    espn_s2: str = ""
    nba_season: str = "2024-25"
    ingest_player_limit: int = 50
    model_dir: str = "models"
    min_games_for_features: int = 5
    rolling_windows: str = "5,10,15"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    artifacts_dir: str = "artifacts"

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
