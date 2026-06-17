# Chiron

NBA Fantasy analytics platform that scrapes player statistics, derives shot-chart computer vision features, engineers ML features, and models simulated fantasy performances for Power BI visualization.

## Architecture

```
[NBA API + ESPN Fantasy] → [Ingestion] → [PostgreSQL]
                              ↓
                    [Shot Chart CV Pipeline]
                              ↓
              [Feature Engineering + Selection + EDA]
                              ↓
                   [XGBoost Training + Simulation]
                              ↓
              [FastAPI] ←→ [Power BI Dashboards]
                              ↓
              [Prometheus + Grafana Monitoring]
```

**Orchestration:** GitHub Actions cron (daily scrape → CV → train)  
**Visualization:** Power BI connected to PostgreSQL views (no Streamlit)  
**CV:** OpenCV analysis of generated shot chart heatmaps  

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env with your ESPN league credentials if needed
```

### 2. Start the stack

```bash
docker compose up -d
```

Services:

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (admin/admin) |
| PostgreSQL | localhost:5432 |

### 3. Run the pipeline

```bash
docker compose --profile pipeline run --rm pipeline
```

Or run stages individually:

```bash
docker compose run --rm api chiron-ingest --limit 10
docker compose run --rm api chiron-cv
docker compose run --rm api chiron-train
```

### 4. Apply Power BI views

```bash
docker compose exec postgres psql -U chiron -d chiron -f /views/views.sql
```

See [powerbi/README.md](powerbi/README.md) for Power BI Desktop connection steps.

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn chiron.api.main:app --reload
pytest tests/ -v
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |
| GET | `/api/v1/players/{id}/projections` | Fantasy point simulations |
| GET | `/api/v1/players/{id}/features` | CV + engineered features |
| GET | `/api/v1/model/runs/latest` | Active model metadata |

## Feature Engineering

Custom metrics (configurable in `config/feature_definitions.yaml`):

- **effort_score** — stocks, rebound rate, minutes trend, shot dispersion
- **overall_shooting_score** — eFG%, TS%, CV zone efficiency, FT rate
- **usage_efficiency** — points per usage %
- **fantasy_volatility** — rolling std of fantasy points

CV features from shot charts:

- `zone_efficiency_score`, `hot_zone_density`, `shot_dispersion`
- `rim_pressure_index`, `left_right_bias`, `cv_overall_shooting_score`

## GitHub Actions

- **CI** (`.github/workflows/ci.yml`) — lint + test on PR
- **Scrape & Train** (`.github/workflows/scrape-train.yml`) — daily cron at 08:00 UTC

Required secrets for cloud pipeline:

- `DATABASE_URL` — when using external Postgres

## Project Structure

```
src/chiron/
├── ingestion/     # NBA + ESPN scrapers
├── cv/            # Shot chart heatmaps + OpenCV features
├── ml/            # EDA, feature engineering, selection, training
├── api/           # FastAPI + Prometheus
└── db/            # SQLAlchemy models + Alembic
monitoring/        # Prometheus + Grafana configs
powerbi/           # SQL views + connection docs
```

## Tech Stack

- Python 3.11, FastAPI, SQLAlchemy, Alembic, Pydantic
- pandas, scikit-learn, XGBoost, OpenCV, nba_api, Playwright
- PostgreSQL, Docker Compose
- Prometheus, Grafana
- Power BI (external visualization)
- GitHub Actions
