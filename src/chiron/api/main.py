import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from chiron.api.metrics import PrometheusMiddleware, metrics_response, update_pipeline_metrics
from chiron.api.routes import router
from chiron.db.session import get_session_factory
from chiron.web.pages import router as web_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parents[1] / "web" / "static"

app = FastAPI(
    title="Chiron API",
    description="NBA Fantasy analytics API",
    version="0.1.0",
)
app.add_middleware(PrometheusMiddleware)
app.include_router(web_router)
app.include_router(router, prefix="/api/v1")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health")
def health_check():
    try:
        session = get_session_factory()()
        session.execute(text("SELECT 1"))
        session.close()
        db_status = "ok"
    except Exception as exc:
        logger.error("Health check DB failure: %s", exc)
        db_status = "error"
    return {"status": "ok" if db_status == "ok" else "degraded", "database": db_status}


@app.get("/metrics")
def metrics():
    try:
        session = get_session_factory()()
        update_pipeline_metrics(session)
        session.close()
    except Exception as exc:
        logger.warning("Could not update pipeline metrics: %s", exc)
    return metrics_response()
