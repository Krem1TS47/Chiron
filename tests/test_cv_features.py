from datetime import date

import pandas as pd

from chiron.cv.features import extract_cv_features_from_shots
from chiron.ingestion.schemas import FantasyScoringRules, PlayerGameStatSchema


def test_compute_fantasy_points():
    from chiron.ingestion.nba_client import compute_fantasy_points

    stat = PlayerGameStatSchema(
        player_id=1,
        game_id="001",
        points=20,
        rebounds=10,
        assists=5,
        steals=2,
        blocks=1,
        turnovers=3,
        fg3_made=4,
    )
    fp = compute_fantasy_points(stat)
    rules = FantasyScoringRules()
    expected = (
        20 * rules.points
        + 10 * rules.rebounds
        + 5 * rules.assists
        + 2 * rules.steals
        + 1 * rules.blocks
        + 3 * rules.turnovers
        + 4 * rules.fg3_made
    )
    assert fp == expected


def test_cv_features_from_shots():
    shots_df = pd.DataFrame(
        [
            {"x": 0, "y": 50, "shot_made": True, "shot_distance": 3},
            {"x": 100, "y": 200, "shot_made": False, "shot_distance": 23},
            {"x": -100, "y": 200, "shot_made": True, "shot_distance": 24},
        ]
    )
    features = extract_cv_features_from_shots(1, date.today(), 5, shots_df)
    assert features.player_id == 1
    assert features.rim_pressure_index is not None
    assert features.cv_overall_shooting_score is not None
    assert 0 <= features.cv_overall_shooting_score <= 1.5


def test_cv_features_empty_shots():
    features = extract_cv_features_from_shots(1, date.today(), 5, pd.DataFrame())
    assert features.zone_efficiency_score is None
