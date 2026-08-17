import argparse
import logging
import sys

from chiron.ingestion.runner import run_ingestion

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full Chiron pipeline")
    parser.add_argument("--skip-ingest", action="store_true")
    parser.add_argument("--skip-cv", action="store_true")
    parser.add_argument("--skip-train", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if not args.skip_ingest:
        logger.info("=== Ingestion ===")
        ingest_result = run_ingestion(player_limit=args.limit)
        logger.info("Ingestion: %s", ingest_result)
        if ingest_result.get("errors", 0) > 0:
            logger.warning("Ingestion completed with errors")
        if ingest_result.get("stats", 0) == 0:
            logger.error("Ingestion produced no game stats; aborting pipeline")
            sys.exit(1)

    if not args.skip_cv:
        from chiron.cv.runner import run_cv_pipeline

        logger.info("=== CV Pipeline ===")
        cv_result = run_cv_pipeline()
        logger.info("CV: %s", cv_result)

    if not args.skip_train:
        from chiron.ml.train.trainer import run_training

        logger.info("=== Training ===")
        train_result = run_training()
        logger.info("Training: %s", train_result)
        if train_result.get("status") == "no_data":
            logger.error("Training has no player-game rows")
            sys.exit(1)

    logger.info("Pipeline complete")


if __name__ == "__main__":
    main()
