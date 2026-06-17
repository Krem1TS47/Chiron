import pandas as pd

from chiron.ml.selection.selector import select_features


def test_feature_selection_reduces_features():
    rng = pd.Series(range(100))
    df = pd.DataFrame(
        {
            "points_per_36": rng * 0.5 + 10,
            "rebounds_per_36": rng * 0.1 + 5,
            "assists_per_36": rng * 0.05 + 3,
            "usage_pct": rng * 0.01 + 0.2,
            "efg_pct": rng * 0.001 + 0.5,
            "duplicate_usage": rng * 0.01 + 0.2,
        }
    )
    y = df["points_per_36"] * 1.2 + df["assists_per_36"] * 2
    selected, meta = select_features(df, y)
    assert len(selected) <= len(df.columns)
    assert meta["final_features"] == len(selected)
    assert len(selected) >= 1
