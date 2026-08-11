"""Name canonicalisation: one franchise per name, one ground per name.

Split out of test_clean.py when that file passed 300 lines. These two functions share a
job — collapsing several written forms of one entity onto its current name — and the same
failure mode: a groupby that reports one thing as several, each with a fraction of its
rows and no error.
"""

from __future__ import annotations

import pandas as pd
import pytest

from scorebook import clean


def frame_from(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


# --- teams ---------------------------------------------------------------------------


def test_renames_collapse_onto_the_current_name():
    frame = frame_from([
        {"batting_team": "Royal Challengers Bangalore", "bowling_team": "Delhi Daredevils"},
        {"batting_team": "Kings XI Punjab", "bowling_team": "Mumbai Indians"},
    ])
    out = clean.canonical_teams(frame)
    assert out["batting_team"].tolist() == ["Royal Challengers Bengaluru", "Punjab Kings"]
    assert out["bowling_team"].tolist() == ["Delhi Capitals", "Mumbai Indians"]


def test_the_one_letter_rename_collapses():
    """Rising Pune Supergiants (2016) and Rising Pune Supergiant (2017) are one franchise
    across its only two seasons. Left alone, every per-team aggregate splits it in two."""
    frame = frame_from([
        {"batting_team": "Rising Pune Supergiants", "bowling_team": "Gujarat Lions"},
        {"batting_team": "Rising Pune Supergiant", "bowling_team": "Gujarat Lions"},
    ])
    out = clean.canonical_teams(frame)
    assert out["batting_team"].nunique() == 1


def test_defunct_franchises_are_not_merged_into_successors():
    """Sunrisers Hyderabad was a new franchise, not a Deccan Chargers rebrand. Merging
    them would invent a continuous history.

    Asserts the whole DEFUNCT_TEAMS set rather than one name, so that constant documents a
    real invariant instead of sitting there unused.
    """
    overlap = clean.DEFUNCT_TEAMS & clean.TEAM_RENAMES.keys()
    assert not overlap, f"defunct franchises must not be renamed away: {overlap}"

    frame = frame_from([{"batting_team": "Deccan Chargers", "bowling_team": "Pune Warriors"}])
    out = clean.canonical_teams(frame)
    assert out["batting_team"].tolist() == ["Deccan Chargers"]
    assert out["bowling_team"].tolist() == ["Pune Warriors"]


def test_canonical_teams_preserves_category_dtype():
    """Renaming must not silently cost the dtype that keeps the real frame at 89 MiB."""
    frame = frame_from([{"batting_team": "Kings XI Punjab", "bowling_team": "Mumbai Indians"}])
    frame["batting_team"] = frame["batting_team"].astype("category")
    out = clean.canonical_teams(frame)
    assert str(out["batting_team"].dtype) == "category"
    assert out["batting_team"].tolist() == ["Punjab Kings"]


def test_canonical_teams_tolerates_a_missing_team_column():
    out = clean.canonical_teams(frame_from([{"batting_team": "Kings XI Punjab"}]))
    assert out["batting_team"].tolist() == ["Punjab Kings"]


def test_canonical_teams_does_not_mutate_its_argument():
    frame = frame_from([{"batting_team": "Kings XI Punjab", "bowling_team": "Mumbai Indians"}])
    clean.canonical_teams(frame)
    assert frame["batting_team"].tolist() == ["Kings XI Punjab"]


# --- venues --------------------------------------------------------------------------


def venue_frame(names: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"venue": pd.Series(names, dtype="category")})


@pytest.mark.parametrize(
    ("written", "expected"),
    [
        # A city suffix that appears in some seasons and not others.
        ("Eden Gardens, Kolkata", "Eden Gardens"),
        ("Wankhede Stadium, Mumbai", "Wankhede Stadium"),
        # Punctuation only.
        ("M.Chinnaswamy Stadium", "M Chinnaswamy Stadium"),
        # A genuine rename, mapped forward like the team names are.
        ("Feroz Shah Kotla", "Arun Jaitley Stadium"),
        ("Sardar Patel Stadium, Motera", "Narendra Modi Stadium"),
        ("Subrata Roy Sahara Stadium", "Maharashtra Cricket Association Stadium"),
    ],
)
def test_venue_spellings_collapse_onto_one_ground(written: str, expected: str):
    assert clean.canonical_venues(venue_frame([written]))["venue"].tolist() == [expected]


def test_chepauk_is_one_ground_not_three():
    """The trap this exists for. Cricsheet writes Chepauk three ways, split almost exactly
    at 2016, so grouping by the raw string shows Chennai abandoning their own ground
    halfway through the league and every home sample looking too small to trust."""
    frame = venue_frame([
        "MA Chidambaram Stadium",
        "MA Chidambaram Stadium, Chepauk",
        "MA Chidambaram Stadium, Chepauk, Chennai",
    ])
    assert clean.canonical_venues(frame)["venue"].nunique() == 1


def test_canonical_venues_preserves_category_dtype():
    out = clean.canonical_venues(venue_frame(["Eden Gardens, Kolkata"]))
    assert str(out["venue"].dtype) == "category"


def test_canonical_venues_handles_a_plain_object_column():
    """The info frame arrives categorical, but a frame built by hand does not."""
    frame = pd.DataFrame({"venue": ["Feroz Shah Kotla", "Eden Gardens, Kolkata"]})
    assert clean.canonical_venues(frame)["venue"].tolist() == [
        "Arun Jaitley Stadium",
        "Eden Gardens",
    ]


def test_canonical_venues_tolerates_a_missing_venue_column():
    frame = frame_from([{"batting_team": "Mumbai Indians"}])
    assert list(clean.canonical_venues(frame).columns) == ["batting_team"]


def test_canonical_venues_does_not_mutate_its_argument():
    frame = venue_frame(["Feroz Shah Kotla"])
    clean.canonical_venues(frame)
    assert frame["venue"].tolist() == ["Feroz Shah Kotla"]


def test_every_rename_target_is_itself_canonical():
    """A two-step rename would leave the first target stranded as its own ground."""
    targets = set(clean.VENUE_RENAMES.values())
    assert not targets & set(clean.VENUE_RENAMES), (
        "a rename target is also a rename key, so one ground still resolves to two names"
    )


