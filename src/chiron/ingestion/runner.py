import argparse
import logging
import sys

from chiron.config import get_settings
from chiron.db.session import get_session_factory
from chiron.ingestion.espn_client import fetch_league_settings, parse_scoring_rules
from chiron.ingestion.nba_client import fetch_active_players, ingest_player
from chiron.ingestion.utils import update_pipeline_metadata

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def run_ingestion(player_limit: int | None = None) -> dict:
    settings = get_settings()
    session = get_session_factory()()
    total = {"players": 0, "games": 0, "stats": 0, "shots": 0, "errors": 0}

    league_json = fetch_league_settings()
    scoring_rules = parse_scoring_rules(league_json) if league_json else None
    if scoring_rules:
        logger.info("Loaded ESPN scoring rules: %s", scoring_rules.model_dump())

    limit = player_limit or settings.ingest_player_limit
    players = fetch_active_players(limit=limit)
    logger.info("Ingesting %d players for season %s", len(players), settings.nba_season)

    for player in players:
        player_id = player["id"]
        try:
            counts = ingest_player(session, player_id, settings.nba_season)
            total["players"] += 1
            total["games"] += counts["games"]
            total["stats"] += counts["stats"]
            total["shots"] += counts["shots"]
        except Exception as exc:
            logger.exception("Failed to ingest player %s: %s", player_id, exc)
            total["errors"] += 1
            session.rollback()

    update_pipeline_metadata(
        session,
        pipeline_name="ingestion",
        status="completed",
        details=total,
        success=total["errors"] == 0,
    )
    session.close()
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Chiron NBA/ESPN ingestion")
    parser.add_argument("--limit", type=int, default=None, help="Max players to ingest")
    args = parser.parse_args()
    result = run_ingestion(player_limit=args.limit)
    logger.info("Ingestion complete: %s", result)
    if result["errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
