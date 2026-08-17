import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert

from chiron.config import get_feature_config, get_settings
from chiron.db.models import FantasyProjection, ModelRun
from chiron.db.session import get_session_factory
from chiron.ingestion.utils import update_pipeline_metadata
from chiron.ml.eda.report import generate_eda_report
from chiron.ml.features.engineering import (
    build_feature_matrix,
    engineer_player_game_features,
    persist_engineered_features,
)
from chiron.ml.selection.selector import select_features

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _time_split(df: pd.DataFrame, split_date: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    split = pd.to_datetime(split_date)
    train = df[pd.to_datetime(df["game_date"]) < split].copy()
    test = df[pd.to_datetime(df["game_date"]) >= split].copy()
    if train.empty or test.empty:
        split_idx = int(len(df) * 0.8)
        train = df.iloc[:split_idx].copy()
        test = df.iloc[split_idx:].copy()
    return train, test


def _simulate_projections(
    model: xgb.XGBRegressor,
    X: pd.DataFrame,
    residuals: np.ndarray,
    n_samples: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    preds = model.predict(X)
    sims = []
    for i in range(len(X)):
        base = preds[i]
        noise = np.random.choice(residuals, size=n_samples, replace=True)
        sims.append(base + noise)
    sims = np.array(sims)
    p10 = np.percentile(sims, 10, axis=1)
    p50 = np.percentile(sims, 50, axis=1)
    p90 = np.percentile(sims, 90, axis=1)
    sim_mean = sims.mean(axis=1)
    sim_std = sims.std(axis=1)
    return p10, p50, p90, sim_mean, sim_std


def run_training() -> dict:
    settings = get_settings()
    config = get_feature_config()
    session = get_session_factory()()

    df = engineer_player_game_features(session)
    if df.empty:
        logger.warning("No data for training")
        session.close()
        return {"status": "no_data"}

    persist_engineered_features(session, df)
    generate_eda_report(df, Path(settings.artifacts_dir) / "eda")

    X, all_features, y = build_feature_matrix(df)
    selected_features, selection_meta = select_features(X, y)

    split_date = config.get("training", {}).get("test_season_start", "2025-10-01")
    train_df, test_df = _time_split(df, split_date)
    X_train = train_df[selected_features].fillna(0)
    y_train = train_df["fantasy_points"].fillna(0)
    X_test = test_df[selected_features].fillna(0)
    y_test = test_df["fantasy_points"].fillna(0)

    model = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    train_pred = model.predict(X_train)
    test_pred = model.predict(X_test)
    selection_metrics = {
        f"selection_{k}": v
        for k, v in selection_meta.items()
        if isinstance(v, (int, float, str))
    }
    metrics = {
        "train_mae": float(mean_absolute_error(y_train, train_pred)),
        "test_mae": float(mean_absolute_error(y_test, test_pred)),
        "train_rmse": float(np.sqrt(mean_squared_error(y_train, train_pred))),
        "test_rmse": float(np.sqrt(mean_squared_error(y_test, test_pred))),
        **selection_metrics,
    }

    model_dir = Path(settings.model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    model_version = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    model_path = model_dir / f"xgb_fantasy_{model_version}.joblib"
    joblib.dump({"model": model, "features": selected_features}, model_path)

    session.execute(update(ModelRun).values(is_active=False))
    run_stmt = insert(ModelRun).values(
        model_name="xgb_fantasy",
        model_version=model_version,
        metrics=metrics,
        feature_manifest=selected_features,
        model_path=str(model_path),
        is_active=True,
    ).returning(ModelRun.id)
    model_run_id = session.scalar(run_stmt)

    residuals = (y_train - train_pred).values
    n_samples = config.get("training", {}).get("simulation_samples", 500)
    p10, p50, p90, sim_mean, sim_std = _simulate_projections(model, X_test, residuals, n_samples)

    for idx, (_, row) in enumerate(test_df.iterrows()):
        proj_stmt = insert(FantasyProjection).values(
            player_id=int(row["player_id"]),
            game_id=str(row["game_id"]),
            model_run_id=model_run_id,
            p10=float(p10[idx]),
            p50=float(p50[idx]),
            p90=float(p90[idx]),
            sim_mean=float(sim_mean[idx]),
            sim_std=float(sim_std[idx]),
        )
        proj_stmt = proj_stmt.on_conflict_do_update(
            constraint="uq_fantasy_projection",
            set_={
                "p10": proj_stmt.excluded.p10,
                "p50": proj_stmt.excluded.p50,
                "p90": proj_stmt.excluded.p90,
                "sim_mean": proj_stmt.excluded.sim_mean,
                "sim_std": proj_stmt.excluded.sim_std,
            },
        )
        session.execute(proj_stmt)

    session.commit()
    update_pipeline_metadata(
        session,
        pipeline_name="training",
        status="completed",
        details={"metrics": metrics, "model_run_id": model_run_id},
        success=True,
    )
    session.close()

    result = {"metrics": metrics, "model_path": str(model_path), "model_run_id": model_run_id}
    logger.info("Training complete: %s", json.dumps(metrics, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Chiron ML training")
    parser.parse_args()
    run_training()


if __name__ == "__main__":
    main()
