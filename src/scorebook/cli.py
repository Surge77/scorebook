"""Command-line entry point: fetch the archive, describe what is in it.

Two verbs and no analysis verb. Answering the questions in docs/questions.md is the
notebook's job — see docs/decisions/0006-analysis-in-notebooks.md.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import clean, describe
from .data import loaders, schemas

_BYTES_PER_MIB = 1024 * 1024


def _force_utf8_output() -> None:
    """Windows consoles default to cp1252, which cannot encode the team names and dashes
    this prints — one UnicodeEncodeError kills the command after the work is done."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def _fetch(args: argparse.Namespace) -> int:
    path = loaders.download_archive(args.cache_dir, force=args.force)
    size = path.stat().st_size / _BYTES_PER_MIB
    print(f"archive ready: {path}  ({size:.1f} MiB)")
    return 0


def _describe(args: argparse.Namespace) -> int:
    if args.sample:
        frame = loaders.load_sample(args.sample)
        source = str(args.sample)
    else:
        frame = loaders.load_deliveries(args.cache_dir)
        source = str(loaders.archive_path(args.cache_dir))

    print(f"source    {source}")
    print(describe.format_summary(describe.summarise(frame), describe.null_profile(frame)))

    if args.clean:
        prepared = clean.prepare(frame)
        added = [column for column in prepared.columns if column not in frame.columns]
        dropped = [column for column in frame.columns if column not in prepared.columns]
        print()
        print("after clean.prepare():")
        print(f"  added     {', '.join(added) or 'nothing'}")
        print(f"  dropped   {', '.join(dropped) or 'nothing'}")
        print(f"  teams     {prepared['batting_team'].nunique()} distinct (after renames)")
        # Both renames collapse values without changing the column count, so neither shows
        # up in `added` or `dropped`. Printed because "what cleaning changed" is the point
        # of this flag, and a silent 60 -> 36 is exactly the kind of change worth seeing.
        print(f"  venues    {prepared['venue'].nunique()} distinct "
              f"(from {frame['venue'].nunique()} written forms)")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scorebook",
        description="Load and inspect Cricsheet's IPL ball-by-ball data.",
    )
    parser.add_argument(
        "--cache-dir", type=Path, default=None,
        help=f"where the archive is cached (default: {loaders.DEFAULT_CACHE_DIR})",
    )
    sub = parser.add_subparsers(dest="command")

    p_fetch = sub.add_parser("fetch", help="download the Cricsheet archive")
    p_fetch.add_argument("--force", action="store_true", help="re-download even if cached")

    p_describe = sub.add_parser("describe", help="summarise the dataset")
    p_describe.add_argument(
        "--sample", type=Path, default=None,
        help="describe a committed sample CSV instead of the full archive (offline)",
    )
    p_describe.add_argument(
        "--clean", action="store_true", help="also report what clean.prepare() changes",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    _force_utf8_output()
    parser = _parser()
    args = parser.parse_args(argv)

    # No subcommand: describe is the useful default, but only if an archive is already
    # cached. Printing help beats a surprise 6.8 MB download.
    if args.command is None:
        if loaders.archive_path(args.cache_dir).exists():
            args.sample, args.clean = None, True
            return _describe(args)
        parser.print_help()
        print("\nNo archive cached yet. Run `scorebook fetch` first.")
        return 0

    handlers = {"fetch": _fetch, "describe": _describe}
    try:
        return handlers[args.command](args)
    except (loaders.DownloadError, schemas.SchemaError, clean.CleaningError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
