"""Shared fixtures.

Unit tests never reach the network. The `archive` fixture builds a real zip containing a
real CSV in `tmp_path`, so the loader is exercised end to end — zip reading, column
validation, dtype assignment — against bytes on disk rather than a mock. The only thing
stubbed out is the download.
"""

from __future__ import annotations

import csv
import io
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from scorebook.data import loaders, schemas

# Two deliveries in one over of one match, then a second match in a slash-labelled
# season. Small enough to reason about, shaped exactly like the real file.
ROWS: tuple[dict[str, object], ...] = (
    {
        "match_id": 1, "season": "2026", "start_date": "2026-03-28",
        "venue": "Wankhede Stadium", "innings": 1, "ball": 0.1,
        "batting_team": "Mumbai Indians", "bowling_team": "Kings XI Punjab",
        "striker": "RG Sharma", "bowler": "A Singh",
        "runs_off_bat": 4, "extras": 0, "wides": "", "noballs": "",
        "wicket_type": "", "player_dismissed": "",
    },
    {
        "match_id": 1, "season": "2026", "start_date": "2026-03-28",
        "venue": "Wankhede Stadium", "innings": 1, "ball": 0.2,
        "batting_team": "Mumbai Indians", "bowling_team": "Kings XI Punjab",
        "striker": "RG Sharma", "bowler": "A Singh",
        "runs_off_bat": 0, "extras": 1, "wides": 1, "noballs": "",
        "wicket_type": "", "player_dismissed": "",
    },
    {
        "match_id": 1, "season": "2026", "start_date": "2026-03-28",
        "venue": "Wankhede Stadium", "innings": 1, "ball": 1.1,
        "batting_team": "Mumbai Indians", "bowling_team": "Kings XI Punjab",
        "striker": "RG Sharma", "bowler": "B Kumar",
        "runs_off_bat": 0, "extras": 0, "wides": "", "noballs": "",
        "wicket_type": "caught", "player_dismissed": "RG Sharma",
    },
    {
        "match_id": 2, "season": "2007/08", "start_date": "2008-04-18",
        "venue": "Eden Gardens", "innings": 1, "ball": 0.1,
        "batting_team": "Royal Challengers Bangalore", "bowling_team": "Delhi Daredevils",
        "striker": "R Dravid", "bowler": "G Gambhir",
        "runs_off_bat": 1, "extras": 0, "wides": "", "noballs": "",
        "wicket_type": "", "player_dismissed": "",
    },
)


def _csv_bytes(columns: tuple[str, ...] = schemas.USED_COLUMNS) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(columns), extrasaction="ignore")
    writer.writeheader()
    writer.writerows(ROWS)
    return buffer.getvalue().encode("utf-8")


@pytest.fixture(autouse=True)
def no_http(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail any unmarked test that opens an HTTP(S) connection.

    Added after a CLI test quietly downloaded the real 6.8 MB archive because it had no
    cached one to find. Discipline did not catch that; a guard does.

    `file://` still works, so the download tests can serve a fixture from tmp_path
    through the same urllib code path a real fetch uses.
    """
    if request.node.get_closest_marker("integration"):
        return

    real_urlopen = urllib.request.urlopen

    def guard(url: object, *args: object, **kwargs: object):
        target = url if isinstance(url, str) else getattr(url, "full_url", "")
        if str(target).startswith(("http://", "https://")):
            raise AssertionError(
                f"unit test attempted a network request to {target}. Stub the boundary, "
                "or mark the test @pytest.mark.integration."
            )
        return real_urlopen(url, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(urllib.request, "urlopen", guard)


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    path = tmp_path / "sample_deliveries.csv"
    path.write_bytes(_csv_bytes())
    return path


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    """An empty cache directory. Never the user's real ~/.cache/scorebook."""
    path = tmp_path / "cache"
    path.mkdir()
    return path


def _build_archive(
    cache_dir: Path,
    *,
    member: str = loaders.DELIVERIES_MEMBER,
    columns: tuple[str, ...] = schemas.USED_COLUMNS,
) -> Path:
    """Write a zip where the loader expects to find its cached archive."""
    path = loaders.archive_path(cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr(member, _csv_bytes(columns))
    return path


@pytest.fixture
def make_archive() -> Callable[..., Path]:
    """Factory, so a test can build a deliberately malformed archive.

    Exposed as a fixture rather than an importable helper: `tests` is not a package, and
    making it one only to share one function is not worth the import path.
    """
    return _build_archive


@pytest.fixture
def archive(cache_dir: Path) -> Path:
    return _build_archive(cache_dir)
