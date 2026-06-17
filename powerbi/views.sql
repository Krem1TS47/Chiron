-- Power BI semantic layer views for Chiron
-- Run after migrations: psql $DATABASE_URL -f powerbi/views.sql

CREATE OR REPLACE VIEW vw_player_game_facts AS
SELECT
    p.id AS player_id,
    p.full_name,
    p.team_abbrev,
    p.position,
    g.id AS game_id,
    g.game_date,
    g.season,
    s.minutes,
    s.points,
    s.rebounds,
    s.assists,
    s.steals,
    s.blocks,
    s.turnovers,
    s.fg3_made,
    s.usage_pct,
    s.efg_pct,
    s.ts_pct,
    s.fantasy_points
FROM player_game_stats s
JOIN players p ON p.id = s.player_id
JOIN games g ON g.id = s.game_id;

CREATE OR REPLACE VIEW vw_cv_features AS
SELECT
    c.player_id,
    p.full_name,
    p.position,
    c.as_of_date,
    c.window_games,
    c.zone_efficiency_score,
    c.hot_zone_density,
    c.shot_dispersion,
    c.rim_pressure_index,
    c.left_right_bias,
    c.cv_overall_shooting_score,
    c.created_at
FROM cv_features c
JOIN players p ON p.id = c.player_id;

CREATE OR REPLACE VIEW vw_fantasy_projections AS
SELECT
    fp.player_id,
    p.full_name,
    p.position,
    fp.game_id,
    g.game_date,
    fp.model_run_id,
    mr.model_version,
    fp.p10,
    fp.p50,
    fp.p90,
    fp.sim_mean,
    fp.sim_std,
    fp.created_at
FROM fantasy_projections fp
JOIN players p ON p.id = fp.player_id
JOIN games g ON g.id = fp.game_id
JOIN model_runs mr ON mr.id = fp.model_run_id
WHERE mr.is_active = TRUE;

CREATE OR REPLACE VIEW vw_model_metrics AS
SELECT
    id AS model_run_id,
    model_name,
    model_version,
    trained_at,
    metrics->>'test_mae' AS test_mae,
    metrics->>'test_rmse' AS test_rmse,
    metrics->>'train_mae' AS train_mae,
    feature_manifest,
    is_active
FROM model_runs
ORDER BY trained_at DESC;

CREATE OR REPLACE VIEW vw_pipeline_freshness AS
SELECT
    pipeline_name,
    last_success_at,
    last_status,
    details,
    updated_at,
    EXTRACT(EPOCH FROM (NOW() - last_success_at)) / 3600 AS hours_since_success
FROM pipeline_metadata;
