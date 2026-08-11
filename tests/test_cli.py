"""Command-line surface. Every path here runs offline."""

from __future__ import annotations

import zipfile
from pathlib import Path

from scorebook import cli


def test_describe_a_sample_prints_the_counts(sample_csv: Path, capsys):
    assert cli.main(["describe", "--sample", str(sample_csv)]) == 0
    out = capsys.readouterr().out
    assert "rows      4" in out
    assert "matches   2" in out
    assert "null %" in out


def test_describe_clean_reports_what_changed(sample_csv: Path, capsys):
    assert cli.main(["describe", "--sample", str(sample_csv), "--clean"]) == 0
    out = capsys.readouterr().out
    assert "after clean.prepare()" in out
    assert "over" in out
    assert "season_year" in out


def test_describe_reads_the_cached_archive(archive: Path, cache_dir: Path, capsys):
    assert archive.exists()
    assert cli.main(["--cache-dir", str(cache_dir), "describe"]) == 0
    assert "rows      4" in capsys.readouterr().out


def test_fetch_reports_the_cached_archive(archive: Path, cache_dir: Path, capsys):
    assert cli.main(["--cache-dir", str(cache_dir), "fetch"]) == 0
    assert "archive ready" in capsys.readouterr().out


def test_fetch_failure_is_a_message_not_a_traceback(cache_dir: Path, capsys, monkeypatch):
    """A network error should read as an error, not a stack trace.

    The download is stubbed at the loader boundary rather than pointed at a dead URL:
    with no cached archive, a real `fetch` would download the real 6.8 MB archive, and a
    unit test must never touch the network.
    """
    def refuse(*_args: object, **_kwargs: object) -> Path:
        raise cli.loaders.DownloadError("connection reset by peer")

    monkeypatch.setattr(cli.loaders, "download_archive", refuse)

    assert cli.main(["--cache-dir", str(cache_dir), "fetch"]) == 1
    assert "error: connection reset by peer" in capsys.readouterr().err
    assert not loaders_archive_exists(cache_dir)


def test_no_subcommand_without_a_cache_prints_help_instead_of_downloading(
    cache_dir: Path, capsys
):
    """A bare `scorebook` must not trigger a surprise 6.8 MB download."""
    assert cli.main(["--cache-dir", str(cache_dir)]) == 0
    out = capsys.readouterr().out
    assert "No archive cached yet" in out
    assert "usage:" in out
    assert not loaders_archive_exists(cache_dir)


def test_no_subcommand_with_a_cache_describes(archive: Path, cache_dir: Path, capsys):
    assert cli.main(["--cache-dir", str(cache_dir)]) == 0
    out = capsys.readouterr().out
    assert "rows      4" in out
    assert "after clean.prepare()" in out


def test_schema_error_is_reported_cleanly(cache_dir: Path, capsys):
    path = cli.loaders.archive_path(cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr("all_matches.csv", "match_id,season\n1,2026\n")

    assert cli.main(["--cache-dir", str(cache_dir), "describe"]) == 1
    assert "error:" in capsys.readouterr().err


def loaders_archive_exists(cache_dir: Path) -> bool:
    return cli.loaders.archive_path(cache_dir).exists()
