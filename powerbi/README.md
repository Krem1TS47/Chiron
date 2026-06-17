# Power BI Integration

Chiron exposes PostgreSQL views designed for Power BI import or DirectQuery. Power BI runs outside Docker (Desktop or Power BI Service).

## Prerequisites

1. Chiron stack running: `docker compose up -d postgres api`
2. Pipeline has run at least once to populate data
3. Views applied: `docker compose exec postgres psql -U chiron -d chiron -f /views/views.sql`

## Connection Settings

| Setting | Value |
|---------|-------|
| Server | `localhost` (or your host IP) |
| Port | `5432` |
| Database | `chiron` |
| Username | `chiron` |
| Password | `chiron` (change in production) |

Connection string example:

```
postgresql://chiron:chiron@localhost:5432/chiron
```

In Power BI Desktop: **Get Data → PostgreSQL database** and enter the settings above.

## Recommended Tables (Views)

Import these views into your semantic model:

| View | Purpose |
|------|---------|
| `vw_player_game_facts` | Player box score facts for explorer pages |
| `vw_cv_features` | Shot chart CV metrics (effort/shooting scores) |
| `vw_fantasy_projections` | Simulated fantasy point distributions |
| `vw_model_metrics` | Model MAE/RMSE and feature manifests |
| `vw_pipeline_freshness` | Pipeline health / data freshness |

## Dashboard Pages

Build these report pages in Power BI:

1. **Player Explorer** — slicers for player/position; line charts for fantasy points; CV shooting scores
2. **Fantasy Simulator** — what-if parameters on projected minutes; distribution bands (p10/p50/p90)
3. **Model Health** — test MAE over model runs; feature importance from `feature_manifest`
4. **Pipeline Freshness** — `vw_pipeline_freshness.hours_since_success` KPI cards

## Refresh Cadence

Align Power BI scheduled refresh with the GitHub Actions cron (default 08:00 UTC daily):

- **Import mode**: schedule refresh after pipeline completes
- **DirectQuery**: projections update on page load (requires network access to Postgres)

## Power BI Service / Gateway

For cloud-hosted Power BI:

1. Install an [On-premises data gateway](https://learn.microsoft.com/en-us/power-bi/connect-data/service-gateway-onprem)
2. Point gateway to your Postgres host (use a secure tunnel or hosted DB in production)
3. Configure scheduled refresh in Power BI Service

## Creating the .pbix Template

Because `.pbix` files are binary and environment-specific, create the template locally:

1. Connect to Postgres using the settings above
2. Load all `vw_*` views
3. Set relationships: `player_id` across facts; `game_id` where applicable
4. Save as `ChironDashboard.pbix` in this folder (gitignored by default)

See [views.sql](./views.sql) for the SQL definitions.
