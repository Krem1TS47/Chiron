from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

COURT_WIDTH = 500
COURT_HEIGHT = 470


def shots_to_dataframe(shots: list[dict]) -> pd.DataFrame:
    if not shots:
        return pd.DataFrame(columns=["x", "y", "shot_made"])
    return pd.DataFrame(shots)


def generate_heatmap_image(
    shots_df: pd.DataFrame,
    output_path: Path,
    title: str = "Shot Chart",
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(5, 4.7))
    ax.set_xlim(-250, 250)
    ax.set_ylim(-47.5, 422.5)
    ax.set_aspect("equal")
    ax.invert_yaxis()
    ax.set_facecolor("#1a1a2e")

    if not shots_df.empty and "x" in shots_df.columns:
        made = shots_df[shots_df["shot_made"] == True]  # noqa: E712
        missed = shots_df[shots_df["shot_made"] == False]  # noqa: E712
        if not made.empty:
            ax.scatter(made["x"], made["y"], c="#2ecc71", alpha=0.6, s=12, label="Made")
        if not missed.empty:
            ax.scatter(missed["x"], missed["y"], c="#e74c3c", alpha=0.5, s=12, label="Miss")
        ax.legend(loc="upper right", fontsize=8)

    ax.set_title(title, color="white", fontsize=10)
    ax.tick_params(colors="white", labelsize=7)
    fig.patch.set_facecolor("#1a1a2e")
    fig.tight_layout()
    fig.savefig(output_path, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)
    return output_path


def generate_density_heatmap_array(
    shots_df: pd.DataFrame,
    size: tuple[int, int] = (128, 120),
) -> np.ndarray:
    heat = np.zeros(size, dtype=np.float32)
    if shots_df.empty:
        return heat

    xs = shots_df["x"].dropna().values
    ys = shots_df["y"].dropna().values
    if len(xs) == 0:
        return heat

    x_norm = ((xs + 250) / 500 * (size[0] - 1)).astype(int)
    y_norm = ((ys + 47.5) / 470 * (size[1] - 1)).astype(int)
    x_norm = np.clip(x_norm, 0, size[0] - 1)
    y_norm = np.clip(y_norm, 0, size[1] - 1)
    for x, y in zip(x_norm, y_norm, strict=False):
        heat[y, x] += 1.0

    if heat.max() > 0:
        heat = heat / heat.max()
    return heat
