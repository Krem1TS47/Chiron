import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from chiron.config import get_settings
from chiron.ml.features.engineering import build_feature_matrix, engineer_player_game_features

logger = logging.getLogger(__name__)


def generate_eda_report(df: pd.DataFrame, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "eda_report.md"

    lines = ["# Chiron EDA Report", ""]
    lines.append(f"- Rows: **{len(df)}**")
    lines.append(f"- Players: **{df['player_id'].nunique() if not df.empty else 0}**")
    lines.append("")

    if df.empty:
        lines.append("_No data available for EDA._")
        report_path.write_text("\n".join(lines), encoding="utf-8")
        return report_path

    lines.append("## Missingness")
    missing = df.isnull().mean().sort_values(ascending=False).head(15)
    for col, pct in missing.items():
        lines.append(f"- `{col}`: {pct:.1%}")
    lines.append("")

    X, feature_cols, y = build_feature_matrix(df)
    lines.append("## Target: Fantasy Points")
    lines.append(f"- Mean: {y.mean():.2f}")
    lines.append(f"- Std: {y.std():.2f}")
    lines.append(f"- Min/Max: {y.min():.2f} / {y.max():.2f}")
    lines.append("")

    fig, ax = plt.subplots(figsize=(8, 4))
    sns.histplot(y, kde=True, ax=ax)
    ax.set_title("Fantasy Points Distribution")
    fig.tight_layout()
    dist_path = output_dir / "fantasy_points_distribution.png"
    fig.savefig(dist_path, dpi=100)
    plt.close(fig)
    lines.append(f"![Fantasy Points Distribution]({dist_path.name})")
    lines.append("")

    if len(feature_cols) > 1:
        corr = X[feature_cols[:20]].corrwith(y).sort_values(key=abs, ascending=False).head(10)
        lines.append("## Top Feature Correlations with Fantasy Points")
        for col, val in corr.items():
            lines.append(f"- `{col}`: {val:.3f}")
        lines.append("")

        corr_matrix = X[feature_cols[:15]].corr()
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(corr_matrix, annot=False, cmap="coolwarm", center=0, ax=ax)
        ax.set_title("Feature Correlation Heatmap")
        fig.tight_layout()
        heatmap_path = output_dir / "correlation_heatmap.png"
        fig.savefig(heatmap_path, dpi=100)
        plt.close(fig)
        lines.append(f"![Correlation Heatmap]({heatmap_path.name})")

    if "position" in df.columns:
        lines.append("")
        lines.append("## Fantasy Points by Position")
        pos_stats = df.groupby("position")["fantasy_points"].agg(["mean", "std", "count"])
        for pos, row in pos_stats.iterrows():
            lines.append(
                f"- {pos}: mean={row['mean']:.2f}, std={row['std']:.2f}, n={int(row['count'])}"
            )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("EDA report written to %s", report_path)
    return report_path


def run_eda() -> Path:
    settings = get_settings()
    from chiron.db.session import get_session_factory

    session = get_session_factory()()
    df = engineer_player_game_features(session)
    session.close()
    output_dir = Path(settings.artifacts_dir) / "eda"
    return generate_eda_report(df, output_dir)
