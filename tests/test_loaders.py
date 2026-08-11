"""Acquisition and loading. Offline except the test explicitly marked `integration`."""

from __future__ import annotations

import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from scorebook.data import loaders, schemas


def test_loads_from_a_cached_archive(archive: Path, cache_dir: Path):
    assert archive.exists()
    frame = loaders.load_deliveries(cache_dir, download=False)
    assert len(frame) == 4
    assert list(frame.columns) == list(schemas.USED_COLUMNS)


def test_low_cardinality_columns_load_as_category(archive: Path, cache_dir: Path):
    """The dtype choice is worth 244 MiB -> 89 MiB on the real file."""
    assert archive.exists()
    frame = loaders.load_deliveries(cache_dir, download=False)
    for column in ("season", "venue", "batting_team"):
        assert str(frame[column].dtype) == "category", column


def test_start_date_is_parsed_to_datetime(archive: Path, cache_dir: Path):
    """Left as text, `start_date` compares lexically — which works for ISO-8601 and quietly
    stops working for anything else, so a string filter passes for a date filter."""
    assert archive.exists()
    frame = loaders.load_deliveries(cache_dir, download=False)
    assert frame["start_date"].dtype.kind == "M"
    # A real date comparison, not a string one.
    assert len(frame[frame["start_date"] >= "2026-01-01"]) == 3


def test_sample_and_archive_agree_on_the_date_dtype(sample_csv: Path, archive: Path,
                                                    cache_dir: Path):
    """The offline and online paths must produce interchangeable frames."""
    assert archive.exists()
    from_sample = loaders.load_sample(sample_csv)
    from_archive = loaders.load_deliveries(cache_dir, download=False)
    assert from_sample["start_date"].dtype == from_archive["start_date"].dtype


def test_refuses_to_download_when_told_not_to(cache_dir: Path):
    with pytest.raises(loaders.DownloadError, match="scorebook fetch"):
        loaders.load_deliveries(cache_dir, download=False)


def test_missing_member_names_the_file_it_wanted(
    cache_dir: Path, make_archive: Callable[..., Path]
):
    make_archive(cache_dir, member="something_else.csv")
    with pytest.raises(schemas.SchemaError, match=r"all_matches\.csv"):
        loaders.load_deliveries(cache_dir, download=False)


def test_dropped_upstream_column_fails_before_parsing(
    cache_dir: Path, make_archive: Callable[..., Path]
):
    """The header is read alone first, so a format change is reported by name instead of
    failing deep inside a 295k-row parse."""
    truncated = tuple(c for c in schemas.USED_COLUMNS if c != "ball")
    make_archive(cache_dir, columns=truncated)
    with pytest.raises(schemas.SchemaError, match="ball"):
        loaders.load_deliveries(cache_dir, download=False)


def test_download_is_skipped_when_already_cached(archive: Path, cache_dir: Path, tmp_path: Path):
    """Pointing at a URL that cannot work proves no request was made."""
    path = loaders.download_archive(cache_dir, url=(tmp_path / "absent.zip").as_uri())
    assert path == archive


def test_download_writes_and_returns_the_archive(cache_dir: Path, tmp_path: Path):
    source = tmp_path / "source.zip"
    with zipfile.ZipFile(source, "w") as bundle:
        # Padded past MIN_ARCHIVE_BYTES so the size guard passes.
        bundle.writestr("all_matches.csv", "x" * (loaders.MIN_ARCHIVE_BYTES + 1))

    path = loaders.download_archive(cache_dir, url=source.as_uri())
    assert path.exists()
    assert zipfile.is_zipfile(path)


def test_download_rejects_a_short_response_and_leaves_no_file(cache_dir: Path, tmp_path: Path):
    """An error page served with HTTP 200 must not be cached as if it were the archive."""
    decoy = tmp_path / "error.html"
    decoy.write_text("<html>404</html>", encoding="utf-8")

    with pytest.raises(loaders.DownloadError, match="outside the expected"):
        loaders.download_archive(cache_dir, url=decoy.as_uri(), attempts=1)
    assert not loaders.archive_path(cache_dir).exists()
    assert not list(cache_dir.glob("*.part")), "the partial download should be cleaned up"


def test_download_rejects_a_non_zip_of_plausible_size(cache_dir: Path, tmp_path: Path):
    decoy = tmp_path / "big.bin"
    decoy.write_bytes(b"\x00" * (loaders.MIN_ARCHIVE_BYTES + 10))

    with pytest.raises(loaders.DownloadError, match="did not return a zip"):
        loaders.download_archive(cache_dir, url=decoy.as_uri(), attempts=1)
    assert not loaders.archive_path(cache_dir).exists()


def test_download_error_is_raised_for_an_unreachable_url(cache_dir: Path, tmp_path: Path):
    """A urllib failure must surface as DownloadError, not a raw URLError.

    Uses a nonexistent file:// URI rather than a dead HTTP port so the conftest network
    guard stays strict — both take the same OSError path inside download_archive.
    """
    with pytest.raises(loaders.DownloadError, match="could not download"):
        loaders.download_archive(cache_dir, url=(tmp_path / "missing.zip").as_uri(), attempts=1)


def _good_archive(tmp_path: Path) -> Path:
    source = tmp_path / "source.zip"
    with zipfile.ZipFile(source, "w") as bundle:
        bundle.writestr("all_matches.csv", "x" * (loaders.MIN_ARCHIVE_BYTES + 1))
    return source


def test_download_retries_a_throttled_response(
    cache_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Cricsheet answers a rate-limited request with a ~12 KB error page and HTTP 200.
    CI hit it twice in one afternoon; both times a rerun a minute later worked. The size
    guard already made it loud, and this makes it survivable."""
    source = _good_archive(tmp_path)
    monkeypatch.setattr(loaders, "RETRY_BACKOFF_SECONDS", 0)

    calls: list[str] = []
    real_download = loaders._download_once

    def throttled_once(url: str, partial: Path) -> None:
        calls.append(url)
        if len(calls) == 1:
            raise loaders.DownloadError("simulated 12 KB throttling page")
        real_download(source.as_uri(), partial)

    monkeypatch.setattr(loaders, "_download_once", throttled_once)

    path = loaders.download_archive(cache_dir, url="https://cricsheet.invalid/ipl.zip")
    assert path.exists()
    assert zipfile.is_zipfile(path)
    assert len(calls) == 2, "the first attempt was refused, the second succeeded"


def test_download_gives_up_and_reports_the_last_failure(
    cache_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    """After the last attempt the useful message is what actually arrived, not a count of
    how many times it was asked for."""
    monkeypatch.setattr(loaders, "RETRY_BACKOFF_SECONDS", 0)
    calls: list[str] = []

    def always_throttled(url: str, partial: Path) -> None:
        calls.append(url)
        raise loaders.DownloadError("outside the expected range")

    monkeypatch.setattr(loaders, "_download_once", always_throttled)

    with pytest.raises(loaders.DownloadError, match="outside the expected range"):
        loaders.download_archive(cache_dir, url="https://cricsheet.invalid/ipl.zip", attempts=3)
    assert len(calls) == 3
    assert not loaders.archive_path(cache_dir).exists()


def test_download_sends_a_descriptive_user_agent(cache_dir: Path, tmp_path: Path,
                                                 monkeypatch: pytest.MonkeyPatch):
    """`Python-urllib/3.11` is exactly the User-Agent a rate limiter looks for."""
    source = _good_archive(tmp_path)
    seen: list[str] = []
    real_urlopen = loaders.urllib.request.urlopen

    def capture(request, *args, **kwargs):
        seen.append(request.get_header("User-agent"))
        return real_urlopen(request, *args, **kwargs)

    monkeypatch.setattr(loaders.urllib.request, "urlopen", capture)
    loaders.download_archive(cache_dir, url=source.as_uri())
    assert seen and seen[0].startswith("scorebook/")


def test_load_sample_validates_columns(sample_csv: Path):
    frame = loaders.load_sample(sample_csv)
    assert len(frame) == 4
    assert str(frame["batting_team"].dtype) == "category"


def test_load_sample_rejects_a_csv_missing_columns(tmp_path: Path):
    bad = tmp_path / "bad.csv"
    bad.write_text("match_id,season\n1,2026\n", encoding="utf-8")
    with pytest.raises(schemas.SchemaError):
        loaders.load_sample(bad)


@pytest.mark.integration
def test_real_archive_parses(tmp_path: Path):
    """Downloads the real 6.8 MB archive. Asserts the counts measured on 2026-08-11 —
    a drift means Cricsheet republished or the loader is dropping rows."""
    frame = loaders.load_deliveries(tmp_path / "cache")
    assert len(frame) >= 295_732
    assert frame["match_id"].nunique() >= 1_243
    assert frame["season"].nunique() >= 19
