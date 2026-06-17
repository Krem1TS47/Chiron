import time

from prometheus_client import Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_COUNT = Counter(
    "chiron_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "chiron_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)
PIPELINE_LAST_SUCCESS = Gauge(
    "chiron_pipeline_last_success_timestamp",
    "Unix timestamp of last successful pipeline run",
    ["pipeline"],
)
RECORDS_INGESTED = Counter(
    "chiron_records_ingested_total",
    "Total records ingested",
    ["record_type"],
)
MODEL_MAE = Gauge("chiron_model_mae", "Latest model test MAE")
PIPELINE_DURATION = Histogram(
    "chiron_pipeline_duration_seconds",
    "Pipeline stage duration",
    ["pipeline"],
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        endpoint = request.url.path
        REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
        REQUEST_LATENCY.labels(request.method, endpoint).observe(duration)
        return response


def metrics_response() -> Response:
    return Response(generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8")


def update_pipeline_metrics(session) -> None:
    from chiron.db.models import ModelRun, PipelineMetadata

    pipelines = session.query(PipelineMetadata).all()
    for p in pipelines:
        if p.last_success_at:
            PIPELINE_LAST_SUCCESS.labels(p.pipeline_name).set(p.last_success_at.timestamp())
        if p.details and "stats" in p.details:
            RECORDS_INGESTED.labels("stats").inc(p.details["stats"])
        if p.details and "shots" in p.details:
            RECORDS_INGESTED.labels("shots").inc(p.details["shots"])

    active_run = (
        session.query(ModelRun)
        .filter_by(is_active=True)
        .order_by(ModelRun.trained_at.desc())
        .first()
    )
    if active_run and active_run.metrics:
        mae = active_run.metrics.get("test_mae")
        if mae is not None:
            MODEL_MAE.set(float(mae))
