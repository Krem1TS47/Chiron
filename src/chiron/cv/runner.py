import argparse
import logging
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from chiron.config import get_settings
from chiron.cv.features import extract_cv_features_from_shots
from chiron.cv.heatmap import generate_heatmap_image
from chiron.db.models import CVFeature, Player, PlayerGameStat, ShotChartImage, ShotEvent
from chiron.db.session import get_session_factory
from chiron.ingestion.utils import update_pipeline_metadata

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _recent_game_ids(session: Session, player_id: int, window: int) -> list[str]:
    stmt = (
        select(PlayerGameStat.game_id)
        .where(PlayerGameStat.player_id == player_id)
        .order_by(PlayerGameStat.id.desc())
        .limit(window)
    )
    return list(session.scalars(stmt).all())


def process_player_cv(
    session: Session,
    player_id: int,
    window_games: int,
    artifacts_dir: Path,
) -> bool:
    as_of = date.today()
    game_ids = _recent_game_ids(session, player_id, window_games)
    if not game_ids:
        return False

    stmt = select(ShotEvent).where(
        ShotEvent.player_id == player_id,
        ShotEvent.game_id.in_(game_ids),
    )
    shots = session.scalars(stmt).all()
    if not shots:
        return False

    shots_data = [
        {
            "x": s.x,
            "y": s.y,
            "shot_made": s.shot_made,
            "shot_distance": s.shot_distance,
        }
        for s in shots
        if s.x is not None and s.y is not None
    ]

    import pandas as pd

    shots_df = pd.DataFrame(shots_data)
    features = extract_cv_features_from_shots(player_id, as_of, window_games, shots_df)

    image_path = artifacts_dir / "shot_charts" / str(player_id) / f"{window_games}.png"
    player = session.get(Player, player_id)
    title = f"{player.full_name if player else player_id} ({window_games}g)"
    generate_heatmap_image(shots_df, image_path, title=title)

    img_stmt = insert(ShotChartImage).values(
        player_id=player_id,
        as_of_date=as_of,
        window_games=window_games,
        image_path=str(image_path),
        source="generated",
    )
    img_stmt = img_stmt.on_conflict_do_update(
        constraint="uq_shot_chart_image",
        set_={"image_path": img_stmt.excluded.image_path, "source": "generated"},
    )
    session.execute(img_stmt)

    cv_stmt = insert(CVFeature).values(**features.model_dump())
    cv_stmt = cv_stmt.on_conflict_do_update(
        constraint="uq_cv_features",
        set_={
            "zone_efficiency_score": cv_stmt.excluded.zone_efficiency_score,
            "hot_zone_density": cv_stmt.excluded.hot_zone_density,
            "shot_dispersion": cv_stmt.excluded.shot_dispersion,
            "rim_pressure_index": cv_stmt.excluded.rim_pressure_index,
            "left_right_bias": cv_stmt.excluded.left_right_bias,
            "cv_overall_shooting_score": cv_stmt.excluded.cv_overall_shooting_score,
        },
    )
    session.execute(cv_stmt)
    session.commit()
    return True


def run_cv_pipeline() -> dict:
    settings = get_settings()
    session = get_session_factory()()
    artifacts_dir = Path(settings.artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    players = session.scalars(select(Player.id)).all()
    counts = {"processed": 0, "skipped": 0, "errors": 0}

    for player_id in players:
        for window in settings.rolling_window_list:
            try:
                ok = process_player_cv(session, player_id, window, artifacts_dir)
                if ok:
                    counts["processed"] += 1
                else:
                    counts["skipped"] += 1
            except Exception as exc:
                logger.exception("CV failed for player %s window %s: %s", player_id, window, exc)
                counts["errors"] += 1
                session.rollback()

    update_pipeline_metadata(
        session,
        pipeline_name="cv",
        status="completed",
        details=counts,
        success=counts["errors"] == 0,
    )
    session.close()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Chiron CV pipeline")
    parser.parse_args()
    result = run_cv_pipeline()
    logger.info("CV pipeline complete: %s", result)


if __name__ == "__main__":
    main()
