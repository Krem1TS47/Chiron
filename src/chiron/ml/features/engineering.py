import logging

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from chiron.config import get_feature_config, get_settings
from chiron.db.models import CVFeature, EngineeredFeature, Game, Player, PlayerGameStat

logger = logging.getLogger(__name__)


def _per_36(value: float | None, minutes: float | None) -> float | None:
    if value is None or minutes is None or minutes <= 0:
        return None
    return value * 36.0 / minutes


def _z_score(series: pd.Series) -> pd.Series:
    std = series.std()
    if std is None or std == 0 or np.isnan(std):
        return pd.Series(0.0, index=series.index)
    return (series - series.mean()) / std


def engineer_player_game_features(session: Session) -> pd.DataFrame:
    settings = get_settings()
    config = get_feature_config()

    stmt = (
        select(
            PlayerGameStat,
            Player.full_name,
            Player.position,
            Game.game_date,
        )
        .join(Player, Player.id == PlayerGameStat.player_id)
        .join(Game, Game.id == PlayerGameStat.game_id)
        .order_by(PlayerGameStat.player_id, Game.game_date)
    )
    rows = session.execute(stmt).all()
    if not rows:
        return pd.DataFrame()

    records = []
    for stat, full_name, position, game_date in rows:
        records.append(
            {
                "player_id": stat.player_id,
                "player_name": full_name,
                "position": position or "UNK",
                "game_id": stat.game_id,
                "game_date": game_date,
                "minutes": stat.minutes,
                "points": stat.points,
                "rebounds": stat.rebounds,
                "assists": stat.assists,
                "steals": stat.steals,
                "blocks": stat.blocks,
                "turnovers": stat.turnovers,
                "fg3_made": stat.fg3_made,
                "usage_pct": stat.usage_pct,
                "efg_pct": stat.efg_pct,
                "ts_pct": stat.ts_pct,
                "fantasy_points": stat.fantasy_points,
            }
        )

    df = pd.DataFrame(records)
    per_36_cols = config.get("normalization", {}).get("per_36_metrics", [])
    for col in per_36_cols:
        if col in df.columns:
            df[f"{col}_per_36"] = df.apply(
                lambda r: _per_36(r.get(col), r.get("minutes")), axis=1
            )

    z_cols = config.get("normalization", {}).get("z_score_by_position", [])
    for col in z_cols:
        if col in df.columns:
            df[f"{col}_z"] = df.groupby("position")[col].transform(_z_score)

    df["stocks"] = df["steals"].fillna(0) + df["blocks"].fillna(0)
    df["minutes_trend"] = df.groupby("player_id")["minutes"].transform(
        lambda s: s.rolling(5, min_periods=1).mean().diff().fillna(0)
    )
    df["fantasy_points_roll_std"] = df.groupby("player_id")["fantasy_points"].transform(
        lambda s: s.rolling(10, min_periods=3).std()
    )

    cv_stmt = select(CVFeature).where(CVFeature.window_games == settings.rolling_window_list[0])
    cv_rows = session.scalars(cv_stmt).all()
    cv_map = {c.player_id: c for c in cv_rows}
    df["shot_dispersion"] = df["player_id"].map(
        lambda pid: getattr(cv_map.get(pid), "shot_dispersion", None)
    )
    df["zone_efficiency_score"] = df["player_id"].map(
        lambda pid: getattr(cv_map.get(pid), "zone_efficiency_score", None)
    )
    df["cv_overall_shooting_score"] = df["player_id"].map(
        lambda pid: getattr(cv_map.get(pid), "cv_overall_shooting_score", None)
    )

    custom = config.get("custom_metrics", {})
    effort_weights = custom.get("effort_score", {}).get("weights", {})
    reb_per_36 = df.get("rebounds_per_36", pd.Series(0)).fillna(0)
    df["effort_score"] = (
        effort_weights.get("stocks", 0.25) * df["stocks"].fillna(0)
        + effort_weights.get("rebounds_per_36", 0.20) * reb_per_36
        + effort_weights.get("minutes_trend", 0.20) * df["minutes_trend"].fillna(0)
        + effort_weights.get("shot_dispersion", 0.15) * df["shot_dispersion"].fillna(0)
        + effort_weights.get("fouls_drawn_per_36", 0.20) * 0
    )

    shoot_weights = custom.get("overall_shooting_score", {}).get("weights", {})
    df["ft_rate"] = df.apply(
        lambda r: (r["fg3_made"] or 0) / max((r.get("minutes") or 1), 1),
        axis=1,
    )
    df["overall_shooting_score"] = (
        shoot_weights.get("efg_pct", 0.30) * df["efg_pct"].fillna(0)
        + shoot_weights.get("ts_pct", 0.25) * df["ts_pct"].fillna(0)
        + shoot_weights.get("zone_efficiency_score", 0.25) * df["zone_efficiency_score"].fillna(0)
        + shoot_weights.get("ft_rate", 0.20) * df["ft_rate"].fillna(0)
    )
    usage = df["usage_pct"].replace(0, np.nan).fillna(0.01)
    df["usage_efficiency"] = df["points"].fillna(0) / usage
    df["fantasy_volatility"] = df["fantasy_points_roll_std"].fillna(0)

    return df


def _feature_columns(df: pd.DataFrame) -> list[str]:
    exclude = {
        "player_id",
        "player_name",
        "position",
        "game_id",
        "game_date",
        "fantasy_points",
    }
    numeric_cols = []
    for col in df.columns:
        if col in exclude:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            numeric_cols.append(col)
    return numeric_cols


def build_feature_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], pd.Series]:
    feature_cols = _feature_columns(df)
    X = df[feature_cols].copy().fillna(0)
    y = df["fantasy_points"].fillna(0)
    return X, feature_cols, y


def persist_engineered_features(session: Session, df: pd.DataFrame) -> int:
    feature_cols = _feature_columns(df)
    count = 0
    for _, row in df.iterrows():
        features = {col: float(row[col]) for col in feature_cols if pd.notna(row.get(col))}
        stmt = insert(EngineeredFeature).values(
            player_id=int(row["player_id"]),
            game_id=str(row["game_id"]),
            feature_version="v1",
            features=features,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_engineered_features",
            set_={"features": stmt.excluded.features, "feature_version": "v1"},
        )
        session.execute(stmt)
        count += 1
    session.commit()
    return count
