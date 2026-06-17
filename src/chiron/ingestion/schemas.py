from datetime import date, datetime

from pydantic import BaseModel, Field


class PlayerSchema(BaseModel):
    id: int
    full_name: str
    team_abbrev: str | None = None
    position: str | None = None
    is_active: bool = True


class GameSchema(BaseModel):
    id: str
    game_date: date
    season: str
    home_team: str | None = None
    away_team: str | None = None


class PlayerGameStatSchema(BaseModel):
    player_id: int
    game_id: str
    minutes: float | None = None
    points: int | None = None
    rebounds: int | None = None
    assists: int | None = None
    steals: int | None = None
    blocks: int | None = None
    turnovers: int | None = None
    fg_made: int | None = None
    fg_attempted: int | None = None
    fg3_made: int | None = None
    fg3_attempted: int | None = None
    ft_made: int | None = None
    ft_attempted: int | None = None
    usage_pct: float | None = None
    pace: float | None = None
    efg_pct: float | None = None
    ts_pct: float | None = None
    fantasy_points: float | None = None


class ShotEventSchema(BaseModel):
    player_id: int
    game_id: str
    event_num: int
    period: int | None = None
    minutes_remaining: int | None = None
    seconds_remaining: int | None = None
    x: float | None = None
    y: float | None = None
    shot_distance: float | None = None
    shot_made: bool = False
    shot_zone: str | None = None


class FantasyScoringRules(BaseModel):
    points: float = 1.0
    rebounds: float = 1.2
    assists: float = 1.5
    steals: float = 3.0
    blocks: float = 3.0
    turnovers: float = -1.0
    fg3_made: float = 0.5


class CVFeatureSchema(BaseModel):
    player_id: int
    as_of_date: date
    window_games: int
    zone_efficiency_score: float | None = None
    hot_zone_density: float | None = None
    shot_dispersion: float | None = None
    rim_pressure_index: float | None = None
    left_right_bias: float | None = None
    cv_overall_shooting_score: float | None = None


class EngineeredFeatureSchema(BaseModel):
    player_id: int
    game_id: str
    feature_version: str = "v1"
    features: dict[str, float] = Field(default_factory=dict)


class FantasyProjectionSchema(BaseModel):
    player_id: int
    game_id: str
    model_run_id: int
    p10: float | None = None
    p50: float | None = None
    p90: float | None = None
    sim_mean: float | None = None
    sim_std: float | None = None


class ModelRunSchema(BaseModel):
    model_name: str
    model_version: str
    trained_at: datetime | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    feature_manifest: list[str] = Field(default_factory=list)
    model_path: str | None = None
    is_active: bool = True
