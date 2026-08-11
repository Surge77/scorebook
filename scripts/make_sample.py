"""Regenerate `data/sample_deliveries.csv` from the real archive.

The sample is the only data committed to this repository, so a fresh clone can run the
tests and open the notebook with no network at all.

It is stratified rather than random: one match from the earliest season and one from the
latest. That is deliberate — those two matches between them carry every awkward case the
cleaning code exists for.

    2007/08   a slash-labelled season, and the pre-rename team names
              (Royal Challengers Bangalore, Delhi Daredevils)
    2026      a plain-year season, and current team names

A random sample would usually contain neither, and the sample would then prove nothing.

    python scripts/make_sample.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from scorebook.data import loaders, schemas

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_PATH = REPO_ROOT / "data" / "sample_deliveries.csv"


def pick_matches(frame: pd.DataFrame) -> list[object]:
    """One match id from the earliest season and one from the latest.

    Ordered by start_date then match_id so the choice is deterministic: rerunning this
    script on the same archive always produces byte-identical output.
    """
    dates = pd.to_datetime(frame["start_date"])
    ordered = frame.assign(_date=dates).sort_values(["_date", "match_id"])
    return [
        ordered["match_id"].iloc[0],
        ordered["match_id"].iloc[-1],
    ]


def build_sample(frame: pd.DataFrame) -> pd.DataFrame:
    chosen = pick_matches(frame)
    sample = frame[frame["match_id"].isin(chosen)].copy()
    # Column order matches the archive, so the sample and the real file are
    # interchangeable inputs to the loader.
    return sample[list(schemas.USED_COLUMNS)]


def main() -> int:
    print("loading the archive (downloads on first run) ...")
    frame = loaders.load_deliveries()

    sample = build_sample(frame)
    SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    # newline="" so pandas controls line endings and the file does not gain \r\n on
    # Windows — otherwise the committed sample churns between machines.
    with SAMPLE_PATH.open("w", encoding="utf-8", newline="") as handle:
        sample.to_csv(handle, index=False)

    seasons = sorted(str(value) for value in sample["season"].unique())
    print(f"wrote {SAMPLE_PATH.relative_to(REPO_ROOT)}")
    print(f"  rows     {len(sample):,}")
    print(f"  matches  {sample['match_id'].nunique()}")
    print(f"  seasons  {', '.join(seasons)}")
    print(f"  bytes    {SAMPLE_PATH.stat().st_size:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
