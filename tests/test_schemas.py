"""The column contract. These tests are the guard against a silent upstream format change."""

from __future__ import annotations

import pytest

from scorebook.data import schemas


def test_used_columns_are_a_subset_of_all_columns():
    """A typo in USED_COLUMNS would otherwise surface as an unexplained pandas KeyError."""
    unknown = set(schemas.USED_COLUMNS) - set(schemas.ALL_COLUMNS)
    assert not unknown, f"USED_COLUMNS names columns the archive does not have: {unknown}"


def test_column_groups_reference_real_columns():
    for name, group in (
        ("CATEGORICAL", schemas.CATEGORICAL),
        ("ALWAYS_EMPTY", schemas.ALWAYS_EMPTY),
        ("INFORMATIVE_NULLS", schemas.INFORMATIVE_NULLS),
        ("EXTRAS_COLUMNS", frozenset(schemas.EXTRAS_COLUMNS)),
    ):
        unknown = group - set(schemas.ALL_COLUMNS)
        assert not unknown, f"{name} names columns the archive does not have: {unknown}"


def test_always_empty_and_informative_nulls_are_disjoint():
    """The distinction is the point: one group gets dropped, the other gets kept.
    A column in both would mean the code contradicts itself about what a null means."""
    assert not (schemas.ALWAYS_EMPTY & schemas.INFORMATIVE_NULLS)


def test_always_empty_columns_are_never_loaded():
    """No point loading 295k rows of a column that is empty in all of them."""
    assert not (set(schemas.USED_COLUMNS) & schemas.ALWAYS_EMPTY)


def test_extras_columns_are_all_informative_nulls():
    assert set(schemas.EXTRAS_COLUMNS) <= schemas.INFORMATIVE_NULLS


def test_validate_columns_accepts_extra_columns():
    """Cricsheet added `actual_delivery` without notice. Extra columns must not fail —
    only missing ones."""
    schemas.validate_columns([*schemas.USED_COLUMNS, "a_new_column_upstream_added"])


def test_validate_columns_names_what_is_missing():
    with pytest.raises(schemas.SchemaError) as caught:
        schemas.validate_columns(["match_id", "season"])
    message = str(caught.value)
    assert "ball" in message
    assert "schemas.py" in message, "the error should say where to fix the contract"
