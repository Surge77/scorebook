"""Summarise a loaded frame — the "did this load correctly?" surface.

Exists because the first question about any dataset is whether you actually got all of
it. The numbers here are what the CI smoke job asserts against, so a loader that
silently drops rows fails the build instead of quietly skewing an average.
"""

from __future__ import annotations

from typing import NamedTuple

import pandas as pd

_BYTES_PER_MIB = 1024 * 1024


class Summary(NamedTuple):
    rows: int
    columns: int
    matches: int
    seasons: int
    first_date: str
    last_date: str
    memory_mib: float


def summarise(frame: pd.DataFrame) -> Summary:
    dates = pd.to_datetime(frame["start_date"])
    return Summary(
        rows=len(frame),
        columns=frame.shape[1],
        matches=int(frame["match_id"].nunique()),
        seasons=int(frame["season"].nunique()),
        first_date=str(dates.min().date()),
        last_date=str(dates.max().date()),
        memory_mib=round(frame.memory_usage(deep=True).sum() / _BYTES_PER_MIB, 1),
    )


def null_profile(frame: pd.DataFrame) -> pd.Series:
    """Null percentage per column, highest first.

    Worth reading before any analysis: in this dataset a high null rate usually means
    "this event rarely happens", not "this data is missing". `wicket_type` is 95% null
    because 95% of deliveries do not take a wicket.
    """
    return (frame.isna().mean() * 100).round(1).sort_values(ascending=False)


def format_summary(summary: Summary, nulls: pd.Series | None = None) -> str:
    """Render a summary as plain text for the CLI."""
    lines = [
        f"rows      {summary.rows:,}",
        f"columns   {summary.columns}",
        f"matches   {summary.matches:,}",
        f"seasons   {summary.seasons}",
        f"dates     {summary.first_date} .. {summary.last_date}",
        f"memory    {summary.memory_mib} MiB",
    ]
    if nulls is not None:
        populated = nulls[nulls > 0]
        if not populated.empty:
            lines.append("")
            lines.append("null % (non-zero only):")
            lines.extend(f"  {name:<22} {value:>5.1f}" for name, value in populated.items())
    return "\n".join(lines)
