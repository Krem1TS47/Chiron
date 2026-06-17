
import cv2
import numpy as np
import pandas as pd

from chiron.ingestion.schemas import CVFeatureSchema


def _classify_zone(x: float, y: float, distance: float | None) -> str:
    if distance is not None and distance <= 4:
        return "restricted"
    if distance is not None and distance <= 14:
        return "paint"
    if distance is not None and distance >= 22:
        if abs(x) >= 220:
            return "corner_3"
        return "above_break_3"
    return "mid_range"


def extract_cv_features_from_shots(
    player_id: int,
    as_of_date,
    window_games: int,
    shots_df: pd.DataFrame,
) -> CVFeatureSchema:
    if shots_df.empty:
        return CVFeatureSchema(
            player_id=player_id,
            as_of_date=as_of_date,
            window_games=window_games,
        )

    df = shots_df.copy()
    df["zone"] = [
        _classify_zone(row.x, row.y, row.shot_distance)
        for row in df.itertuples(index=False)
    ]

    zone_stats = df.groupby("zone").agg(
        attempts=("shot_made", "count"),
        makes=("shot_made", "sum"),
    )
    zone_stats["fg_pct"] = zone_stats["makes"] / zone_stats["attempts"].replace(0, np.nan)
    weights = {
        "restricted": 1.2,
        "paint": 1.0,
        "mid_range": 0.8,
        "corner_3": 1.1,
        "above_break_3": 1.0,
    }
    zone_efficiency = 0.0
    total_weight = 0.0
    for zone, row in zone_stats.iterrows():
        w = weights.get(zone, 1.0)
        if pd.notna(row["fg_pct"]):
            zone_efficiency += float(row["fg_pct"]) * w
            total_weight += w
    zone_efficiency_score = zone_efficiency / total_weight if total_weight else 0.0

    heat = np.zeros((128, 120), dtype=np.float32)
    xs = df["x"].dropna().values
    ys = df["y"].dropna().values
    for x, y in zip(xs, ys, strict=False):
        xi = int(np.clip((x + 250) / 500 * 127, 0, 127))
        yi = int(np.clip((y + 47.5) / 470 * 119, 0, 119))
        heat[yi, xi] += 1.0
    if heat.max() > 0:
        heat /= heat.max()

    _, thresh = cv2.threshold((heat * 255).astype(np.uint8), 127, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    hot_zone_density = float(len(contours))

    flat = heat.flatten()
    flat = flat[flat > 0]
    if len(flat) > 0:
        probs = flat / flat.sum()
        shot_dispersion = float(-np.sum(probs * np.log(probs + 1e-9)))
    else:
        shot_dispersion = 0.0

    rim_mask = df["shot_distance"].fillna(999) <= 4
    rim_pressure_index = float(rim_mask.mean()) if len(df) else 0.0

    left_attempts = (df["x"] < 0).sum()
    right_attempts = (df["x"] >= 0).sum()
    total_attempts = left_attempts + right_attempts
    left_right_bias = (
        float(abs(left_attempts - right_attempts) / total_attempts) if total_attempts else 0.0
    )

    cv_overall_shooting_score = (
        0.35 * zone_efficiency_score
        + 0.20 * min(hot_zone_density / 5.0, 1.0)
        + 0.15 * min(shot_dispersion / 3.0, 1.0)
        + 0.15 * rim_pressure_index
        + 0.15 * (1.0 - left_right_bias)
    )

    return CVFeatureSchema(
        player_id=player_id,
        as_of_date=as_of_date,
        window_games=window_games,
        zone_efficiency_score=round(zone_efficiency_score, 4),
        hot_zone_density=round(hot_zone_density, 4),
        shot_dispersion=round(shot_dispersion, 4),
        rim_pressure_index=round(rim_pressure_index, 4),
        left_right_bias=round(left_right_bias, 4),
        cv_overall_shooting_score=round(cv_overall_shooting_score, 4),
    )
