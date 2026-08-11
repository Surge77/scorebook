"""Acquire the Cricsheet IPL archive and load it into a DataFrame.

One outbound request, to one public URL, with no credentials. The archive is cached
outside the repository so it is downloaded once per machine and never committed.
"""

from __future__ import annotations

import shutil
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from . import schemas

ARCHIVE_URL = "https://cricsheet.org/downloads/ipl_csv2.zip"

# The aggregated ball-by-ball file. The archive also holds 1,243 per-match pairs
# (<id>.csv and <id>_info.csv); the _info files are key-value long format, not tabular,
# and are out of scope for now — see README "Known limits".
DELIVERIES_MEMBER = "all_matches.csv"

# Cache lives beside the other tool caches, not in the project. Overridable so tests
# never touch the real one.
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "scorebook"

# The archive was 6.8 MB in August 2026 and grows by a season each year. These bounds
# only catch a truncated download or an error page served with HTTP 200 — they are
# deliberately loose, because a tight upper bound would break every May.
MIN_ARCHIVE_BYTES = 1_000_000
MAX_ARCHIVE_BYTES = 200_000_000

DOWNLOAD_TIMEOUT_SECONDS = 30


class DownloadError(RuntimeError):
    """The archive could not be fetched, or what arrived was not a usable zip."""


def archive_path(cache_dir: Path | None = None) -> Path:
    return (cache_dir or DEFAULT_CACHE_DIR) / "ipl_csv2.zip"


def download_archive(
    cache_dir: Path | None = None,
    *,
    force: bool = False,
    url: str = ARCHIVE_URL,
) -> Path:
    """Download the archive to the cache and return its path. A no-op when cached.

    Raises DownloadError rather than letting a urllib exception escape, so the CLI can
    print something a human can act on.
    """
    target = archive_path(cache_dir)
    if target.exists() and not force:
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    # Download to a sibling temp file and move into place only on success, so an
    # interrupted download cannot leave a truncated archive that looks cached.
    partial = target.with_suffix(".zip.part")
    try:
        with (
            urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response,
            partial.open("wb") as handle,
        ):
            shutil.copyfileobj(response, handle)
    except OSError as error:
        partial.unlink(missing_ok=True)
        raise DownloadError(f"could not download {url}: {error}") from error

    size = partial.stat().st_size
    if not MIN_ARCHIVE_BYTES <= size <= MAX_ARCHIVE_BYTES:
        partial.unlink(missing_ok=True)
        raise DownloadError(
            f"{url} returned {size:,} bytes, outside the expected "
            f"{MIN_ARCHIVE_BYTES:,}-{MAX_ARCHIVE_BYTES:,} range. "
            "Refusing to cache it; the URL may be serving an error page."
        )
    if not zipfile.is_zipfile(partial):
        partial.unlink(missing_ok=True)
        raise DownloadError(f"{url} did not return a zip archive.")

    partial.replace(target)
    return target


def _read_member(archive: Path, columns: tuple[str, ...]) -> pd.DataFrame:
    """Stream one named member out of the zip.

    Uses ZipFile.open() on an exact member name and never extractall(), so a crafted
    archive cannot write anywhere on disk. See SECURITY.md.
    """
    with zipfile.ZipFile(archive) as bundle:
        if DELIVERIES_MEMBER not in bundle.namelist():
            raise schemas.SchemaError(
                f"{archive} does not contain {DELIVERIES_MEMBER}. "
                "Cricsheet may have renamed it; update DELIVERIES_MEMBER."
            )
        # Read the header alone first so a format change is reported by name rather
        # than as a pandas KeyError partway through a 295k-row parse.
        with bundle.open(DELIVERIES_MEMBER) as handle:
            header = pd.read_csv(handle, nrows=0)
        schemas.validate_columns(list(header.columns), expected=columns)

        dtypes = {name: "category" for name in columns if name in schemas.CATEGORICAL}
        with bundle.open(DELIVERIES_MEMBER) as handle:
            # low_memory=False parses in one pass rather than in chunks. Chunked parsing
            # infers dtypes per chunk, and the all-null columns (non_boundary, fielder_3)
            # come out as mixed types with a DtypeWarning — which, under this project's
            # filterwarnings=["error"], is a test failure for anyone loading ALL_COLUMNS.
            frame = pd.read_csv(
                handle, usecols=list(columns), dtype=dtypes, low_memory=False
            )
        return _parse_dates(frame)


def _parse_dates(frame: pd.DataFrame) -> pd.DataFrame:
    """Give `start_date` a real datetime dtype.

    Left as text it compares lexically, which happens to work for ISO-8601 and silently
    stops working for anything else — `frame[frame.start_date > "2020-01-01"]` looks like a
    date filter and is a string filter. Parsing once here also means `add_season_year` and
    `describe.summarise` read the same values rather than each parsing independently.
    """
    if schemas.DATE_COLUMN in frame.columns:
        frame[schemas.DATE_COLUMN] = pd.to_datetime(
            frame[schemas.DATE_COLUMN], format=schemas.DATE_FORMAT
        )
    return frame


def load_deliveries(
    cache_dir: Path | None = None,
    *,
    columns: tuple[str, ...] = schemas.USED_COLUMNS,
    download: bool = True,
) -> pd.DataFrame:
    """Load ball-by-ball deliveries, downloading the archive first if needed.

    Pass `download=False` to fail loudly instead of reaching the network — what the
    offline unit tests do.
    """
    target = archive_path(cache_dir)
    if not target.exists():
        if not download:
            raise DownloadError(
                f"no cached archive at {target} and download=False. "
                "Run `scorebook fetch` first."
            )
        target = download_archive(cache_dir)
    return _read_member(target, columns)


def load_sample(path: Path) -> pd.DataFrame:
    """Load the committed sample CSV — the offline path a fresh clone uses."""
    dtypes = {name: "category" for name in schemas.USED_COLUMNS if name in schemas.CATEGORICAL}
    frame = pd.read_csv(path, dtype=dtypes)
    schemas.validate_columns(list(frame.columns))
    return _parse_dates(frame)
