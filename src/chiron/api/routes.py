from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from chiron.db.models import CVFeature, EngineeredFeature, FantasyProjection, ModelRun, Player
from chiron.db.session import get_db

router = APIRouter()


@router.get("/players/{player_id}/projections")
def get_player_projections(player_id: int, db: Session = Depends(get_db)):
    player = db.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    active_run = db.scalars(
        select(ModelRun).where(ModelRun.is_active.is_(True)).order_by(ModelRun.trained_at.desc())
    ).first()
    if not active_run:
        return {"player_id": player_id, "projections": []}

    projections = db.scalars(
        select(FantasyProjection)
        .where(
            FantasyProjection.player_id == player_id,
            FantasyProjection.model_run_id == active_run.id,
        )
        .order_by(FantasyProjection.id.desc())
        .limit(20)
    ).all()

    return {
        "player_id": player_id,
        "player_name": player.full_name,
        "model_run_id": active_run.id,
        "projections": [
            {
                "game_id": p.game_id,
                "p10": p.p10,
                "p50": p.p50,
                "p90": p.p90,
                "sim_mean": p.sim_mean,
                "sim_std": p.sim_std,
            }
            for p in projections
        ],
    }


@router.get("/players/{player_id}/features")
def get_player_features(player_id: int, db: Session = Depends(get_db)):
    player = db.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    cv_features = db.scalars(
        select(CVFeature)
        .where(CVFeature.player_id == player_id)
        .order_by(CVFeature.as_of_date.desc())
        .limit(5)
    ).all()

    engineered = db.scalars(
        select(EngineeredFeature)
        .where(EngineeredFeature.player_id == player_id)
        .order_by(EngineeredFeature.id.desc())
        .limit(5)
    ).all()

    return {
        "player_id": player_id,
        "player_name": player.full_name,
        "cv_features": [
            {
                "as_of_date": str(c.as_of_date),
                "window_games": c.window_games,
                "zone_efficiency_score": c.zone_efficiency_score,
                "hot_zone_density": c.hot_zone_density,
                "shot_dispersion": c.shot_dispersion,
                "rim_pressure_index": c.rim_pressure_index,
                "left_right_bias": c.left_right_bias,
                "cv_overall_shooting_score": c.cv_overall_shooting_score,
            }
            for c in cv_features
        ],
        "engineered_features": [
            {"game_id": e.game_id, "features": e.features} for e in engineered
        ],
    }


@router.get("/model/runs/latest")
def get_latest_model_run(db: Session = Depends(get_db)):
    run = db.scalars(
        select(ModelRun).where(ModelRun.is_active.is_(True)).order_by(ModelRun.trained_at.desc())
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="No model runs found")
    return {
        "id": run.id,
        "model_name": run.model_name,
        "model_version": run.model_version,
        "trained_at": run.trained_at.isoformat() if run.trained_at else None,
        "metrics": run.metrics,
        "feature_manifest": run.feature_manifest,
        "model_path": run.model_path,
    }
