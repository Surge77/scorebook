"""Chart styling and saving. Deliberately no chart builders.

This module sets up a figure and writes it out. It does not aggregate anything and it
does not decide what kind of chart your question deserves — those are the analysis, and
the analysis lives in the notebook.

Cricket has its own names for these charts, and using them costs nothing:

    Manhattan    runs per over, as bars — the skyline shape is the name
    worm         cumulative runs against balls faced, one line per innings
    wagon wheel  runs radiating out by the direction they were hit
    pitch map    where deliveries landed, as a 2-D scatter on the pitch

See docs/glossary.md.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

# Agg: a non-interactive backend, chosen so that importing this module never tries to
# open a window. Without it, tests and CI fail on a headless machine.
matplotlib.use("Agg")

# These imports must follow the matplotlib.use() call above, not precede it.
import matplotlib.pyplot as plt

# Figure and Axes come from their own modules, not from pyplot. pyplot re-exports them at
# runtime but its type stubs do not, so annotating with plt.Figure fails type checking.
from matplotlib.axes import Axes
from matplotlib.figure import Figure

DEFAULT_REPORTS_DIR = Path("reports")

# One figure size everywhere, so charts sit together in a README without rescaling.
FIGURE_SIZE = (9.0, 5.0)
FIGURE_DPI = 130


def new_figure(title: str, xlabel: str, ylabel: str) -> tuple[Figure, Axes]:
    """A figure with the house style and every axis already labelled.

    Labels are required arguments rather than optional keywords on purpose: an unlabelled
    axis is the single most common way a chart becomes unreadable a week later.
    """
    figure, axes = plt.subplots(figsize=FIGURE_SIZE, dpi=FIGURE_DPI)
    axes.set_title(title)
    axes.set_xlabel(xlabel)
    axes.set_ylabel(ylabel)
    axes.grid(True, alpha=0.3, linewidth=0.6)
    axes.spines[["top", "right"]].set_visible(False)
    return figure, axes


def save_fig(figure: Figure, name: str, reports_dir: Path | None = None) -> Path:
    """Write a figure to reports/ as PNG and return the path.

    `reports/` is gitignored: charts are regenerated from code, never committed, so the
    repo cannot drift from a stale image.
    """
    target_dir = reports_dir or DEFAULT_REPORTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / (name if name.endswith(".png") else f"{name}.png")
    figure.tight_layout()
    figure.savefig(path)
    plt.close(figure)
    return path
