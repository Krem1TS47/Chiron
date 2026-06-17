import logging
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from chiron.db.models import PipelineMetadata

logger = logging.getLogger(__name__)


def update_pipeline_metadata(
    session: Session,
    pipeline_name: str,
    status: str,
    details: dict | None = None,
    success: bool = True,
) -> None:
    now = datetime.now(timezone.utc)
    record = session.query(PipelineMetadata).filter_by(pipeline_name=pipeline_name).first()
    if record is None:
        record = PipelineMetadata(pipeline_name=pipeline_name)
        session.add(record)
    record.last_status = status
    record.details = details or {}
    if success:
        record.last_success_at = now
    record.updated_at = now
    session.commit()
    logger.info("Pipeline %s status=%s success=%s", pipeline_name, status, success)


def rate_limit(seconds: float = 0.6) -> None:
    time.sleep(seconds)
