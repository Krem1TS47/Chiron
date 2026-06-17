"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-06-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("full_name", sa.String(length=128), nullable=False),
        sa.Column("team_abbrev", sa.String(length=8), nullable=True),
        sa.Column("position", sa.String(length=8), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "games",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("game_date", sa.Date(), nullable=False),
        sa.Column("season", sa.String(length=16), nullable=False),
        sa.Column("home_team", sa.String(length=8), nullable=True),
        sa.Column("away_team", sa.String(length=8), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_games_game_date", "games", ["game_date"])
    op.create_table(
        "pipeline_metadata",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pipeline_name", sa.String(length=64), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(length=32), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pipeline_name"),
    )
    op.create_table(
        "model_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False),
        sa.Column("trained_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("feature_manifest", sa.JSON(), nullable=True),
        sa.Column("model_path", sa.String(length=512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "player_game_stats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.String(length=32), nullable=False),
        sa.Column("minutes", sa.Float(), nullable=True),
        sa.Column("points", sa.Integer(), nullable=True),
        sa.Column("rebounds", sa.Integer(), nullable=True),
        sa.Column("assists", sa.Integer(), nullable=True),
        sa.Column("steals", sa.Integer(), nullable=True),
        sa.Column("blocks", sa.Integer(), nullable=True),
        sa.Column("turnovers", sa.Integer(), nullable=True),
        sa.Column("fg_made", sa.Integer(), nullable=True),
        sa.Column("fg_attempted", sa.Integer(), nullable=True),
        sa.Column("fg3_made", sa.Integer(), nullable=True),
        sa.Column("fg3_attempted", sa.Integer(), nullable=True),
        sa.Column("ft_made", sa.Integer(), nullable=True),
        sa.Column("ft_attempted", sa.Integer(), nullable=True),
        sa.Column("usage_pct", sa.Float(), nullable=True),
        sa.Column("pace", sa.Float(), nullable=True),
        sa.Column("efg_pct", sa.Float(), nullable=True),
        sa.Column("ts_pct", sa.Float(), nullable=True),
        sa.Column("fantasy_points", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", "game_id", name="uq_player_game"),
    )
    op.create_index("ix_player_game_stats_player_id", "player_game_stats", ["player_id"])
    op.create_index("ix_player_game_stats_game_id", "player_game_stats", ["game_id"])
    op.create_table(
        "shot_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.String(length=32), nullable=False),
        sa.Column("event_num", sa.Integer(), nullable=False),
        sa.Column("period", sa.Integer(), nullable=True),
        sa.Column("minutes_remaining", sa.Integer(), nullable=True),
        sa.Column("seconds_remaining", sa.Integer(), nullable=True),
        sa.Column("x", sa.Float(), nullable=True),
        sa.Column("y", sa.Float(), nullable=True),
        sa.Column("shot_distance", sa.Float(), nullable=True),
        sa.Column("shot_made", sa.Boolean(), nullable=True),
        sa.Column("shot_zone", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", "game_id", "event_num", name="uq_shot_event"),
    )
    op.create_index("ix_shot_events_player_id", "shot_events", ["player_id"])
    op.create_index("ix_shot_events_game_id", "shot_events", ["game_id"])
    op.create_table(
        "shot_chart_images",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("window_games", sa.Integer(), nullable=False),
        sa.Column("image_path", sa.String(length=512), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", "as_of_date", "window_games", name="uq_shot_chart_image"),
    )
    op.create_index("ix_shot_chart_images_player_id", "shot_chart_images", ["player_id"])
    op.create_table(
        "cv_features",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("window_games", sa.Integer(), nullable=False),
        sa.Column("zone_efficiency_score", sa.Float(), nullable=True),
        sa.Column("hot_zone_density", sa.Float(), nullable=True),
        sa.Column("shot_dispersion", sa.Float(), nullable=True),
        sa.Column("rim_pressure_index", sa.Float(), nullable=True),
        sa.Column("left_right_bias", sa.Float(), nullable=True),
        sa.Column("cv_overall_shooting_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", "as_of_date", "window_games", name="uq_cv_features"),
    )
    op.create_index("ix_cv_features_player_id", "cv_features", ["player_id"])
    op.create_table(
        "engineered_features",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.String(length=32), nullable=False),
        sa.Column("feature_version", sa.String(length=32), nullable=True),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", "game_id", name="uq_engineered_features"),
    )
    op.create_index("ix_engineered_features_player_id", "engineered_features", ["player_id"])
    op.create_index("ix_engineered_features_game_id", "engineered_features", ["game_id"])
    op.create_table(
        "fantasy_projections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.String(length=32), nullable=False),
        sa.Column("model_run_id", sa.Integer(), nullable=False),
        sa.Column("p10", sa.Float(), nullable=True),
        sa.Column("p50", sa.Float(), nullable=True),
        sa.Column("p90", sa.Float(), nullable=True),
        sa.Column("sim_mean", sa.Float(), nullable=True),
        sa.Column("sim_std", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["model_run_id"], ["model_runs.id"]),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", "game_id", "model_run_id", name="uq_fantasy_projection"),
    )
    op.create_index("ix_fantasy_projections_player_id", "fantasy_projections", ["player_id"])
    op.create_index("ix_fantasy_projections_game_id", "fantasy_projections", ["game_id"])


def downgrade() -> None:
    op.drop_table("fantasy_projections")
    op.drop_table("engineered_features")
    op.drop_table("cv_features")
    op.drop_table("shot_chart_images")
    op.drop_table("shot_events")
    op.drop_table("player_game_stats")
    op.drop_table("model_runs")
    op.drop_table("pipeline_metadata")
    op.drop_table("games")
    op.drop_table("players")
