from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chiron.db.base import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    team_abbrev: Mapped[str | None] = mapped_column(String(8))
    position: Mapped[str | None] = mapped_column(String(8))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    game_stats: Mapped[list["PlayerGameStat"]] = relationship(back_populates="player")
    shot_events: Mapped[list["ShotEvent"]] = relationship(back_populates="player")


class Game(Base):
    __tablename__ = "games"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    game_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    season: Mapped[str] = mapped_column(String(16), nullable=False)
    home_team: Mapped[str | None] = mapped_column(String(8))
    away_team: Mapped[str | None] = mapped_column(String(8))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    player_stats: Mapped[list["PlayerGameStat"]] = relationship(back_populates="game")


class PlayerGameStat(Base):
    __tablename__ = "player_game_stats"
    __table_args__ = (UniqueConstraint("player_id", "game_id", name="uq_player_game"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False, index=True)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"), nullable=False, index=True)
    minutes: Mapped[float | None] = mapped_column(Float)
    points: Mapped[int | None] = mapped_column(Integer)
    rebounds: Mapped[int | None] = mapped_column(Integer)
    assists: Mapped[int | None] = mapped_column(Integer)
    steals: Mapped[int | None] = mapped_column(Integer)
    blocks: Mapped[int | None] = mapped_column(Integer)
    turnovers: Mapped[int | None] = mapped_column(Integer)
    fg_made: Mapped[int | None] = mapped_column(Integer)
    fg_attempted: Mapped[int | None] = mapped_column(Integer)
    fg3_made: Mapped[int | None] = mapped_column(Integer)
    fg3_attempted: Mapped[int | None] = mapped_column(Integer)
    ft_made: Mapped[int | None] = mapped_column(Integer)
    ft_attempted: Mapped[int | None] = mapped_column(Integer)
    usage_pct: Mapped[float | None] = mapped_column(Float)
    pace: Mapped[float | None] = mapped_column(Float)
    efg_pct: Mapped[float | None] = mapped_column(Float)
    ts_pct: Mapped[float | None] = mapped_column(Float)
    fantasy_points: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    player: Mapped["Player"] = relationship(back_populates="game_stats")
    game: Mapped["Game"] = relationship(back_populates="player_stats")


class ShotEvent(Base):
    __tablename__ = "shot_events"
    __table_args__ = (UniqueConstraint("player_id", "game_id", "event_num", name="uq_shot_event"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False, index=True)
    game_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    event_num: Mapped[int] = mapped_column(Integer, nullable=False)
    period: Mapped[int | None] = mapped_column(Integer)
    minutes_remaining: Mapped[int | None] = mapped_column(Integer)
    seconds_remaining: Mapped[int | None] = mapped_column(Integer)
    x: Mapped[float | None] = mapped_column(Float)
    y: Mapped[float | None] = mapped_column(Float)
    shot_distance: Mapped[float | None] = mapped_column(Float)
    shot_made: Mapped[bool] = mapped_column(default=False)
    shot_zone: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    player: Mapped["Player"] = relationship(back_populates="shot_events")


class ShotChartImage(Base):
    __tablename__ = "shot_chart_images"
    __table_args__ = (
        UniqueConstraint("player_id", "as_of_date", "window_games", name="uq_shot_chart_image"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False, index=True)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    window_games: Mapped[int] = mapped_column(Integer, nullable=False)
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="generated")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CVFeature(Base):
    __tablename__ = "cv_features"
    __table_args__ = (
        UniqueConstraint("player_id", "as_of_date", "window_games", name="uq_cv_features"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False, index=True)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    window_games: Mapped[int] = mapped_column(Integer, nullable=False)
    zone_efficiency_score: Mapped[float | None] = mapped_column(Float)
    hot_zone_density: Mapped[float | None] = mapped_column(Float)
    shot_dispersion: Mapped[float | None] = mapped_column(Float)
    rim_pressure_index: Mapped[float | None] = mapped_column(Float)
    left_right_bias: Mapped[float | None] = mapped_column(Float)
    cv_overall_shooting_score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EngineeredFeature(Base):
    __tablename__ = "engineered_features"
    __table_args__ = (
        UniqueConstraint("player_id", "game_id", name="uq_engineered_features"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False, index=True)
    game_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    feature_version: Mapped[str] = mapped_column(String(32), default="v1")
    features: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelRun(Base):
    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    feature_manifest: Mapped[list[str]] = mapped_column(JSON, default=list)
    model_path: Mapped[str | None] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(default=True)


class FantasyProjection(Base):
    __tablename__ = "fantasy_projections"
    __table_args__ = (
        UniqueConstraint("player_id", "game_id", "model_run_id", name="uq_fantasy_projection"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False, index=True)
    game_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    model_run_id: Mapped[int] = mapped_column(ForeignKey("model_runs.id"), nullable=False)
    p10: Mapped[float | None] = mapped_column(Float)
    p50: Mapped[float | None] = mapped_column(Float)
    p90: Mapped[float | None] = mapped_column(Float)
    sim_mean: Mapped[float | None] = mapped_column(Float)
    sim_std: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PipelineMetadata(Base):
    __tablename__ = "pipeline_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pipeline_name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str | None] = mapped_column(String(32))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
