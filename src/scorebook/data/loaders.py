"""Acquire the Cricsheet IPL archive and load it into a DataFrame.

One outbound request, to one public URL, with no credentials. The archive is cached
outside the repository so it is downloaded once per machine and never committed.
"""

from __future__ import annotations

import csv
import io
import shutil
import time
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from .. import __version__
from . import schemas

ARCHIVE_URL = "https://cricsheet.org/downloads/ipl_csv2.zip"

# The aggregated ball-by-ball file. The archive also holds 1,243 per-match pairs
# (<id>.csv and <id>_info.csv). The _info files are key-value long format rather than
# tabular and are read separately by load_match_info().
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

# Cricsheet serves an error page — around 12 KB, with HTTP 200 — when it throttles, and it
# does throttle: two CI runs on one afternoon got one instead of the archive. The size
# guard below catches it, so the failure is loud rather than a corrupt parse, but a single
# attempt turns a transient refusal into a red build and a wasted rerun.
DOWNLOAD_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 3.0

# urllib's default User-Agent is `Python-urllib/3.11`, which is exactly what a rate limiter
# is looking for. Saying who this is and where it came from is both politer and less likely
# to be challenged.
USER_AGENT = f"scorebook/{__version__} (+https://github.com/Surge77/scorebook)"


class DownloadError(RuntimeError):
    """The archive could not be fetched, or what arrived was not a usable zip."""


def archive_path(cache_dir: Path | None = None) -> Path:
    return (cache_dir or DEFAULT_CACHE_DIR) / "ipl_csv2.zip"


def _download_once(url: str, partial: Path) -> None:
    """Fetch `url` into `partial`, or raise DownloadError and leave no file behind.

    Every failure path unlinks the partial, so a rejected attempt cannot leave a
    truncated file that the next call mistakes for a cached archive.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with (
            urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response,
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


def download_archive(
    cache_dir: Path | None = None,
    *,
    force: bool = False,
    url: str = ARCHIVE_URL,
    attempts: int = DOWNLOAD_ATTEMPTS,
) -> Path:
    """Download the archive to the cache and return its path. A no-op when cached.

    Retries a rejected response with a linear backoff, because the rejection this most
    often sees is a throttling page rather than a broken URL. The last failure is raised
    as-is: after three refusals the useful message is what actually arrived, not "retried
    three times". Pass `attempts=1` to fail on the first.

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
    for attempt in range(1, attempts + 1):
        try:
            _download_once(url, partial)
            break
        except DownloadError:
            if attempt == attempts:
                raise
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)

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


def _ensure_archive(cache_dir: Path | None, *, download: bool) -> Path:
    """Return the cached archive path, downloading it if allowed.

    Shared by both loaders so the two cannot drift into giving different advice about
    the same missing file.
    """
    target = archive_path(cache_dir)
    if target.exists():
        return target
    if not download:
        raise DownloadError(
            f"no cached archive at {target} and download=False. "
            "Run `scorebook fetch` first."
        )
    return download_archive(cache_dir)


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
    return _read_member(_ensure_archive(cache_dir, download=download), columns)


def load_sample(path: Path) -> pd.DataFrame:
    """Load the committed sample CSV — the offline path a fresh clone uses."""
    dtypes = {name: "category" for name in schemas.USED_COLUMNS if name in schemas.CATEGORICAL}
    frame = pd.read_csv(path, dtype=dtypes)
    schemas.validate_columns(list(frame.columns))
    return _parse_dates(frame)


def _parse_info_member(raw: bytes, member: str) -> dict[str, str | None]:
    """Pivot one `<id>_info.csv` from key-value rows into a single record.

    Repeated keys take their first value, which is what `setdefault` buys: two matches
    carry a second `date` row for a reserve day, and the start date is the one that
    belongs beside the deliveries.
    """
    record: dict[str, str | None] = {}
    teams: list[str] = []
    for row in csv.reader(io.StringIO(raw.decode("utf-8"))):
        # `version,2.3.0` has no key column, and a `player` row has a third field that
        # would be read as a value if the key were not checked first.
        if len(row) < 3 or row[0] != "info":
            continue
        key, value = row[1], row[2]
        if key == schemas.INFO_TEAM_KEY:
            teams.append(value)
        elif key == schemas.INFO_DATE_KEY:
            record.setdefault("start_date", value)
        elif key in schemas.INFO_SCALAR_KEYS:
            record.setdefault(key, value)

    # Both are present in all 1,243 members today. Missing either is an upstream format
    # change, and both fail silently if allowed through: no match_id cannot be joined to
    # the deliveries, and no date yields a NaT that quietly drops the row out of every
    # date filter and season grouping rather than raising.
    for required, key in (("match_id", "match_id"), (schemas.DATE_COLUMN, "date")):
        if required not in record:
            raise schemas.SchemaError(
                f"{member} has no `info,{key}` row. The upstream info format may have "
                "changed; update src/scorebook/data/schemas.py."
            )
    # Padded rather than indexed: an abandoned fixture with one named team should come
    # back with a null opponent, not an IndexError.
    padded = [*teams, None, None]
    record["team_1"], record["team_2"] = padded[0], padded[1]
    return record


def load_match_info(cache_dir: Path | None = None, *, download: bool = True) -> pd.DataFrame:
    """Load one row per match from the 1,243 `<id>_info.csv` members.

    Returns `schemas.INFO_COLUMNS`, joinable to the deliveries on `match_id`. This is the
    only source of match *outcomes* — who won, who won the toss, which city it was played
    in — none of which appear in the ball-by-ball file.

    `winner` is null on 25 matches: 16 ties and 9 no-results. The ties were decided by a
    super over and their winner is in `eliminator`, so whether a super-over win counts as
    a win is left to the caller rather than settled here.

    Team names come through exactly as written, which means the pre-rename ones are still
    present. Pass the team columns through `clean.canonical_teams` before grouping:

        info = clean.canonical_teams(
            loaders.load_match_info(),
            columns=("team_1", "team_2", "toss_winner", "winner"),
        )

    See docs/decisions/0007-reading-the-info-files.md.
    """
    archive = _ensure_archive(cache_dir, download=download)
    records: list[dict[str, str | None]] = []
    with zipfile.ZipFile(archive) as bundle:
        # Sorted so the frame's row order is stable between runs; namelist() order is
        # whatever the zip happens to store.
        members = sorted(
            name for name in bundle.namelist()
            if name.endswith(schemas.INFO_MEMBER_SUFFIX)
        )
        if not members:
            raise schemas.SchemaError(
                f"{archive} contains no *{schemas.INFO_MEMBER_SUFFIX} members. "
                "Cricsheet may have changed the archive layout."
            )
        for member in members:
            # ZipFile.open() on an exact name, never extractall(). See SECURITY.md.
            with bundle.open(member) as handle:
                records.append(_parse_info_member(handle.read(), member))

    frame = pd.DataFrame.from_records(records, columns=list(schemas.INFO_COLUMNS))
    frame["match_id"] = frame["match_id"].astype("int64")
    for column in ("winner_runs", "winner_wickets"):
        # Nullable Int16, not int: these two are mutually exclusive by construction, so
        # whichever did not decide the match is genuinely absent rather than zero.
        frame[column] = pd.to_numeric(frame[column]).astype("Int16")
    for column in schemas.INFO_CATEGORICAL:
        frame[column] = frame[column].astype("category")
    frame[schemas.DATE_COLUMN] = pd.to_datetime(
        frame[schemas.DATE_COLUMN], format=schemas.INFO_DATE_FORMAT
    )
    return frame
