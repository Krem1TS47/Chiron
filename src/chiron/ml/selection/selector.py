import logging

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.feature_selection import f_regression, mutual_info_regression

from chiron.config import get_feature_config

logger = logging.getLogger(__name__)


def _drop_low_variance(X: pd.DataFrame, threshold: float) -> pd.DataFrame:
    variances = X.var()
    keep = variances[variances >= threshold].index.tolist()
    return X[keep]


def _drop_high_correlation(X: pd.DataFrame, threshold: float) -> list[str]:
    corr = X.corr().abs()
    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
    to_drop = [col for col in upper.columns if any(upper[col] > threshold)]
    return [c for c in X.columns if c not in to_drop]


def select_features(
    X: pd.DataFrame,
    y: pd.Series,
) -> tuple[list[str], dict]:
    config = get_feature_config().get("feature_selection", {})
    corr_threshold = config.get("correlation_threshold", 0.95)
    var_threshold = config.get("variance_threshold", 0.01)
    top_k = config.get("top_k_univariate", 40)

    X_filtered = _drop_low_variance(X, var_threshold)
    remaining = _drop_high_correlation(X_filtered, corr_threshold)

    if len(remaining) == 0:
        remaining = list(X.columns)

    X_sub = X_filtered[remaining]
    mi = mutual_info_regression(X_sub.fillna(0), y.fillna(0), random_state=42)
    mi_rank = pd.Series(mi, index=X_sub.columns).sort_values(ascending=False)
    mi_selected = mi_rank.head(top_k).index.tolist()

    f_scores, _ = f_regression(X_sub[mi_selected].fillna(0), y.fillna(0))
    f_rank = pd.Series(f_scores, index=mi_selected).sort_values(ascending=False)
    univariate_selected = f_rank.head(min(top_k, len(f_rank))).index.tolist()

    model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_sub[univariate_selected].fillna(0), y.fillna(0))
    importance = pd.Series(model.feature_importances_, index=univariate_selected)
    importance = importance.sort_values(ascending=False)
    final_features = importance.head(min(25, len(importance))).index.tolist()

    metadata = {
        "initial_features": len(X.columns),
        "after_variance_filter": len(X_filtered.columns),
        "after_correlation_filter": len(remaining),
        "univariate_selected": len(univariate_selected),
        "final_features": len(final_features),
        "top_importance": importance.head(10).to_dict(),
    }
    logger.info("Feature selection: %s -> %s features", len(X.columns), len(final_features))
    return final_features, metadata
