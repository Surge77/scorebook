"""Chart styling and saving. Not the charts themselves — those live in the notebook."""

from __future__ import annotations

from pathlib import Path

from scorebook import plots


def test_new_figure_labels_every_axis():
    """Labels are required arguments precisely so this can never be empty."""
    figure, axes = plots.new_figure("Runs per over", "Over", "Runs")
    try:
        assert axes.get_title() == "Runs per over"
        assert axes.get_xlabel() == "Over"
        assert axes.get_ylabel() == "Runs"
        assert not axes.spines["top"].get_visible()
    finally:
        plots.plt.close(figure)


def test_save_fig_writes_a_png_and_creates_the_directory(tmp_path: Path):
    figure, axes = plots.new_figure("t", "x", "y")
    axes.plot([0, 1], [0, 1])
    target = tmp_path / "nested" / "reports"

    path = plots.save_fig(figure, "manhattan", reports_dir=target)

    assert path == target / "manhattan.png"
    assert path.stat().st_size > 0


def test_save_fig_does_not_double_the_extension(tmp_path: Path):
    figure, _ = plots.new_figure("t", "x", "y")
    path = plots.save_fig(figure, "worm.png", reports_dir=tmp_path)
    assert path.name == "worm.png"


def test_backend_is_headless():
    """Agg, so importing this module never tries to open a window — otherwise CI hangs
    or fails on a machine with no display."""
    assert plots.matplotlib.get_backend().lower() == "agg"
