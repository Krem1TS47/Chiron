import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from chiron.db.models import CVFeature, FantasyProjection, ModelRun, PipelineMetadata, Player
from chiron.db.session import get_db

logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))
router = APIRouter()


def _latest_model_run(db: Session) -> ModelRun | None:
    return db.scalars(
        select(ModelRun).where(ModelRun.is_active.is_(True)).order_by(ModelRun.trained_at.desc())
    ).first()


@router.get("/", response_class=HTMLResponse)
def dashboard_home(request: Request, db: Session = Depends(get_db)):
    players: list[Player] = []
    pipelines: list[PipelineMetadata] = []
    model_run = None
    try:
        players = list(db.scalars(select(Player).order_by(Player.full_name)).all())
        pipelines = list(
            db.scalars(select(PipelineMetadata).order_by(PipelineMetadata.pipeline_name)).all()
        )
        model_run = _latest_model_run(db)
    except Exception as exc:
        logger.warning("Dashboard home DB failure: %s", exc)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "players": players,
            "pipelines": pipelines,
            "model_run": model_run,
        },
    )


@router.get("/players/{player_id}", response_class=HTMLResponse)
def dashboard_player(request: Request, player_id: int, db: Session = Depends(get_db)):
    try:
        player = db.get(Player, player_id)
    except Exception as exc:
        logger.warning("Dashboard player DB failure: %s", exc)
        return templates.TemplateResponse(
            request,
            "player.html",
            {
                "player": None,
                "player_id": player_id,
                "projections": [],
                "cv_features": [],
                "unavailable": True,
            },
        )

    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    active_run = _latest_model_run(db)
    projections = []
    if active_run:
        projections = list(
            db.scalars(
                select(FantasyProjection)
                .where(
                    FantasyProjection.player_id == player_id,
                    FantasyProjection.model_run_id == active_run.id,
                )
                .order_by(FantasyProjection.id.desc())
                .limit(20)
            ).all()
        )
    cv_features = list(
        db.scalars(
            select(CVFeature)
            .where(CVFeature.player_id == player_id)
            .order_by(CVFeature.as_of_date.desc())
            .limit(5)
        ).all()
    )
    return templates.TemplateResponse(
        request,
        "player.html",
        {
            "player": player,
            "player_id": player_id,
            "projections": projections,
            "cv_features": cv_features,
            "unavailable": False,
        },
    )
